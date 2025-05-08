# handlers/auto_send.py
import asyncio
from telegram.error import TelegramError, BadRequest, Forbidden
from utils.news_fetcher import news_fetcher
from utils.helpers import format_news
from database.db import Database
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database()

# Cache per le notizie inviate
last_sent_news = {}


async def send_news_to_subscribers(bot, category: str, force_update: bool = False):
    """Invia notizie a tutti gli iscritti alla categoria"""
    print(f"[DEBUG] Starting news sending for category: {category}")

    try:
        # Ottieni i dati degli iscritti con le loro preferenze
        subscribers = db.get_subscribers(category)
        print(f"[DEBUG] Found {len(subscribers)} subscribers for {category}")

        if not subscribers:
            print(f"[DEBUG] No subscribers for {category}, skipping")
            return 0

        # Ottieni le notizie
        news = await news_fetcher.get_news(category, limit=5)
        print(f"[DEBUG] Fetched {len(news)} news items for {category}")

        if not news:
            print(f"[DEBUG] No news found for {category}")
            return 0

        # Verifica se ci sono notizie nuove rispetto all'ultimo invio
        if category in last_sent_news and not force_update:
            last_news_urls = {item[1] for item in last_sent_news[category]}
            current_news_urls = {item[1] for item in news}

            # Se non ci sono nuove notizie, salta l'invio
            if current_news_urls.issubset(last_news_urls):
                print(f"[DEBUG] No new news for {category}, skipping")
                return 0

            # Filtra solo le notizie nuove
            new_news = [item for item in news if item[1] not in last_news_urls]
            if new_news:
                news = new_news
                print(f"[DEBUG] Sending only {len(news)} new news items")

        # Aggiorna la cache
        last_sent_news[category] = news

        # Contatore di invii riusciti
        successful_sends = 0

        # Invia le notizie a ciascun iscritto
        for user_id, user_prefs in subscribers.items():
            try:
                # Rispetta le preferenze dell'utente per la frequenza di invio
                frequency = user_prefs.get('frequency', 'normal')

                # Salta alcuni invii per gli utenti con frequenza bassa
                if frequency == 'low' and datetime.now().hour % 4 != 0:
                    print(f"[DEBUG] Skipping user {user_id} due to low frequency setting")
                    continue

                # Personalizza il formato in base alle preferenze dell'utente
                show_sources = user_prefs.get('show_sources', True)
                max_items = user_prefs.get('max_items', 5)

                # Seleziona solo le prime N notizie in base alle preferenze
                user_news = news[:max_items]

                print(f"[DEBUG] Sending {len(user_news)} news to user {user_id}")

                # Formatta le notizie
                formatted_news = format_news(user_news, include_source=show_sources)

                # Prepara il messaggio con intestazione
                message = f"📰 *Ultime notizie {category.upper()}*\n\n{formatted_news}"

                # Invia il messaggio
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

                successful_sends += 1

                # Aggiorna la statistica nel database
                db.increment_news_sent(user_id)

                # Piccola pausa per evitare di raggiungere i limiti di Telegram
                await asyncio.sleep(0.1)

            except Forbidden:
                # L'utente ha bloccato il bot
                print(f"[INFO] User {user_id} has blocked the bot, removing from subscribers")
                db.remove_subscriber(user_id, category)
                logger.info(f"User {user_id} removed from {category} subscribers (blocked bot)")

            except BadRequest as e:
                # Chat non trovata o altri errori
                if "chat not found" in str(e).lower():
                    print(f"[INFO] Chat with user {user_id} not found, removing from subscribers")
                    db.remove_subscriber(user_id, category)
                    logger.info(f"User {user_id} removed from {category} subscribers (chat not found)")
                else:
                    logger.error(f"BadRequest when sending to {user_id}: {e}")
                    print(f"[ERROR] BadRequest for {user_id}: {e}")

            except TelegramError as e:
                logger.error(f"Telegram error when sending to {user_id}: {e}")
                print(f"[ERROR] Failed to send to {user_id}: {e}")

            except Exception as e:
                logger.error(f"Unexpected error when sending to {user_id}: {e}")
                print(f"[ERROR] Failed to send to {user_id}: {e}")

        # Registra l'evento di invio nel database
        db.log_news_sent(category, successful_sends)
        print(f"[INFO] Successfully sent news to {successful_sends}/{len(subscribers)} subscribers")

        return successful_sends

    except Exception as e:
        logger.error(f"General error in send_news_to_subscribers: {e}")
        print(f"[ERROR] General error in send_news_to_subscribers: {e}")
        return 0


def setup_periodic_jobs(application, scheduler):
    """Configura i job periodici"""
    print("[DEBUG] Setting up periodic jobs")

    # Notizie generali ogni 2 ore
    scheduler.add_job(
        send_news_to_subscribers,
        'interval',
        hours=1,
        args=[application.bot, 'generale'],
        id='general_news'
    )

    # Notizie per piattaforme ogni 3 ore
    for platform in ['ps5', 'xbox', 'switch', 'pc']:
        scheduler.add_job(
            send_news_to_subscribers,
            'interval',
            hours=2,
            args=[application.bot, platform],
            id=f'{platform}_news'
        )

    # Notizie tech ogni 4 ore
    scheduler.add_job(
        send_news_to_subscribers,
        'interval',
        hours=3,
        args=[application.bot, 'tech'],
        id='tech_news'
    )

    # Notizie IA ogni 6 ore
    scheduler.add_job(
        send_news_to_subscribers,
        'interval',
        hours=4,
        args=[application.bot, 'ia'],
        id='ia_news'
    )

    # Notizie cripto ogni 6 ore
    scheduler.add_job(
        send_news_to_subscribers,
        'interval',
        hours=5,
        args=[application.bot, 'cripto'],
        id='cripto_news'
    )

    # Reset della cache giornaliero
    scheduler.add_job(
        reset_cache,
        'cron',
        hour=0,
        minute=0,
        id='reset_cache'
    )

    # Job di pulizia per rimuovere gli utenti inattivi mensilmente
    scheduler.add_job(
        cleanup_inactive_users,
        'cron',
        day=1,
        hour=1,
        minute=0,
        args=[application.bot],  # Aggiunto il parametro bot
        id='cleanup_inactive'
    )

    print("[DEBUG] Periodic jobs setup completed")


def reset_cache():
    """Resetta la cache delle notizie inviate"""
    print("[DEBUG] Resetting news cache")
    global last_sent_news
    last_sent_news = {}


async def cleanup_inactive_users(bot):
    """Rimuove gli utenti inattivi dal database"""
    print("[DEBUG] Running cleanup of inactive users")
    try:
        # Ottieni gli utenti inattivi (non hanno interagito con il bot per X giorni)
        inactive_users = db.get_inactive_users(days=60)

        if not inactive_users:
            print("[INFO] No inactive users to clean up")
            return

        print(f"[INFO] Found {len(inactive_users)} inactive users")

        removed = 0
        for user_id in inactive_users:
            try:
                # Invia un messaggio di notifica
                await bot.send_message(
                    chat_id=user_id,
                    text="📢 *Avviso di inattività*\n\n"
                         "Non hai interagito con il bot negli ultimi 60 giorni. "
                         "Se desideri continuare a ricevere notizie, "
                         "invia un qualsiasi messaggio o comando entro 7 giorni, "
                         "altrimenti sarai rimosso dalla lista degli iscritti.",
                    parse_mode="Markdown"
                )

                # Segna l'utente per la rimozione se non risponde
                db.mark_for_removal(user_id)

            except (Forbidden, BadRequest):
                # L'utente ha già bloccato il bot o eliminato la chat
                db.remove_user(user_id)
                removed += 1

            except Exception as e:
                logger.error(f"Error during cleanup for user {user_id}: {e}")

        print(f"[INFO] Removed {removed} inactive users")

    except Exception as e:
        logger.error(f"Error in cleanup_inactive_users: {e}")
        print(f"[ERROR] Failed to clean up inactive users: {e}")


async def send_digest(bot, user_id, categories=None):
    """Invia un riepilogo delle notizie all'utente"""
    try:
        if categories is None:
            # Usa le categorie a cui l'utente è iscritto
            categories = db.get_user_categories(user_id)

        if not categories:
            categories = ['generale']

        all_news = []

        for category in categories:
            news = await news_fetcher.get_news(category, limit=3)
            if news:
                all_news.append(f"📌 *{category.upper()}*:")
                all_news.append(format_news(news, include_source=True))

        if all_news:
            message = "📰 *RIEPILOGO GIORNALIERO*\n\n" + "\n\n".join(all_news)

            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Error sending digest to {user_id}: {e}")
        return False