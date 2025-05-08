import asyncio
from telegram.error import TelegramError, BadRequest, Forbidden
from utils.news_fetcher import news_fetcher
from utils.helpers import format_news
from database.db import Database
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)
db = Database()

# Cache per le notizie inviate
last_sent_news: Dict[str, List[Tuple[str, str, str]]] = {}

# Aggiungi in cima al file
GROUP_IDS = {
    'generale': [-100123456789],  # Sostituisci con il tuo ID gruppo
    'tech': [-100123456789],      # Stesso gruppo o altri
}

async def send_news_to_subscribers(bot, category: str, force_update: bool = False) -> int:
    logger.info(f"Avvio invio notizie per categoria: {category}")

    # Ottieni sia gli iscritti dal DB che i gruppi fissi
    subscribers = db.get_subscribers(category)
    group_ids = GROUP_IDS.get(category, [])

    # Combina i destinatari
    all_recipients = {**subscribers}
    for group_id in group_ids:
        all_recipients[group_id] = {'frequency': 'normal', 'show_sources': True, 'max_items': 5}

    logger.info(
        f"Trovati {len(all_recipients)} destinatari per {category} (iscritti: {len(subscribers)}, gruppi: {len(group_ids)})")
    """Invia notizie a tutti gli iscritti alla categoria specificata."""
    try:
        subscribers = db.get_subscribers(category)
        logger.info(f"Trovati {len(subscribers)} iscritti per {category}")

        if not subscribers:
            logger.info(f"Nessun iscritto per {category}, operazione annullata")
            return 0

        try:
            news = await news_fetcher.get_news(category, limit=5)
            logger.info(f"Recuperate {len(news)} notizie per {category}")
        except Exception as e:
            logger.error(f"Errore nel recupero notizie per {category}: {e}")
            return 0

        if not news:
            logger.info(f"Nessuna notizia trovata per {category}")
            return 0

        if not force_update and category in last_sent_news:
            last_news_urls = {item[1] for item in last_sent_news[category]}
            current_news_urls = {item[1] for item in news}

            if current_news_urls.issubset(last_news_urls):
                logger.info(f"Nessuna notizia nuova per {category}, operazione annullata")
                return 0

            new_news = [item for item in news if item[1] not in last_news_urls]
            if new_news:
                news = new_news
                logger.info(f"Invio solo {len(news)} nuove notizie")

        last_sent_news[category] = news
        successful_sends = 0

        for user_id, user_prefs in subscribers.items():
            try:
                # Verifica preliminare se l'utente ha bloccato il bot
                try:
                    chat = await bot.get_chat(user_id)
                    if chat.type == 'private' and not chat.has_active_bot():
                        logger.info(f"Utente {user_id} ha bloccato il bot, rimozione...")
                        db.remove_subscriber(user_id, category)
                        continue
                except Exception as e:
                    logger.warning(f"Errore verifica chat utente {user_id}: {e}")

                frequency = user_prefs.get('frequency', 'normal')
                if frequency == 'low' and datetime.now().hour % 4 != 0:
                    logger.debug(f"Salto utente {user_id} per impostazione frequenza bassa")
                    continue

                show_sources = user_prefs.get('show_sources', True)
                max_items = min(user_prefs.get('max_items', 5), 10)
                user_news = news[:max_items]

                logger.info(f"Invio {len(user_news)} notizie all'utente {user_id}")
                formatted_news = format_news(user_news, include_source=show_sources)
                message = f"📰 *Ultime notizie {category.upper()}*\n\n{formatted_news}"

                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

                successful_sends += 1
                db.increment_news_sent(user_id)
                await asyncio.sleep(0.2)

            except Forbidden:
                logger.info(f"Utente {user_id} ha bloccato il bot, rimozione dagli iscritti")
                db.remove_subscriber(user_id, category)

            except BadRequest as e:
                if "chat not found" in str(e).lower():
                    logger.info(f"Chat con utente {user_id} non trovata, rimozione dagli iscritti")
                    db.remove_subscriber(user_id, category)
                else:
                    logger.error(f"BadRequest durante l'invio a {user_id}: {e}")

            except TelegramError as e:
                logger.error(f"Errore Telegram durante l'invio a {user_id}: {e}")

            except Exception as e:
                logger.error(f"Errore imprevisto durante l'invio a {user_id}: {e}", exc_info=True)

        db.log_news_sent(category, successful_sends)
        logger.info(f"Notizie inviate con successo a {successful_sends}/{len(subscribers)} iscritti")
        return successful_sends

    except Exception as e:
        logger.error(f"Errore generale in send_news_to_subscribers: {e}", exc_info=True)
        return 0


def setup_periodic_jobs(application, scheduler):
    """Configura i job periodici per l'invio automatico di notizie."""
    logger.info("Configurazione job periodici")

    try:
        for job_id in ['general_news', 'ps5_news', 'xbox_news',
                     'switch_news', 'pc_news', 'tech_news',
                     'ia_news', 'cripto_news', 'reset_cache',
                     'cleanup_inactive']:
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass

        scheduler.add_job(
            send_news_to_subscribers,
            trigger='interval',
            hours=1,
            args=[application.bot, 'generale'],
            id='general_news'
        )

        for platform in ['ps5', 'xbox', 'switch', 'pc']:
            scheduler.add_job(
                send_news_to_subscribers,
                trigger='interval',
                hours=2,
                args=[application.bot, platform],
                id=f'{platform}_news'
            )

        scheduler.add_job(
            send_news_to_subscribers,
            trigger='interval',
            hours=3,
            args=[application.bot, 'tech'],
            id='tech_news'
        )

        scheduler.add_job(
            send_news_to_subscribers,
            trigger='interval',
            hours=4,
            args=[application.bot, 'ia'],
            id='ia_news'
        )

        scheduler.add_job(
            send_news_to_subscribers,
            trigger='interval',
            hours=5,
            args=[application.bot, 'cripto'],
            id='cripto_news'
        )

        scheduler.add_job(
            reset_cache,
            trigger='cron',
            hour=0,
            minute=0,
            id='reset_cache'
        )

        scheduler.add_job(
            cleanup_inactive_users,
            trigger='cron',
            day=1,
            hour=1,
            minute=0,
            args=[application.bot],
            id='cleanup_inactive'
        )

        logger.info("Job periodici configurati correttamente")
        logger.debug(f"Job attivi: {scheduler.get_jobs()}")

    except Exception as e:
        logger.error(f"Errore nella configurazione dei job periodici: {e}", exc_info=True)
        raise


def reset_cache():
    """Resetta la cache delle notizie inviate."""
    global last_sent_news
    logger.info("Reset cache notizie inviate")
    last_sent_news = {}


async def cleanup_inactive_users(bot):
    """Rimuove gli utenti inattivi dal database."""
    logger.info("Avvio pulizia utenti inattivi")

    try:
        inactive_users = db.get_inactive_users(days=60)

        if not inactive_users:
            logger.info("Nessun utente inattivo da pulire")
            return

        logger.info(f"Trovati {len(inactive_users)} utenti inattivi")
        removed = 0

        for user_id in inactive_users:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="📢 *Avviso di inattività*\n\n"
                         "Non hai interagito con il bot negli ultimi 60 giorni. "
                         "Se desideri continuare a ricevere notizie, "
                         "invia un qualsiasi messaggio o comando entro 7 giorni, "
                         "altrimenti sarai rimosso dalla lista degli iscritti.",
                    parse_mode="Markdown"
                )

                db.mark_for_removal(user_id)
                removed += 1

            except (Forbidden, BadRequest):
                db.remove_user(user_id)
                removed += 1
                logger.info(f"Rimosso utente {user_id} (chat non disponibile)")

            except Exception as e:
                logger.error(f"Errore durante la pulizia per utente {user_id}: {e}")

        logger.info(f"Pulizia completata, rimossi {removed} utenti inattivi")

    except Exception as e:
        logger.error(f"Errore nella pulizia utenti inattivi: {e}", exc_info=True)


async def send_digest(bot, user_id: int, categories: Optional[List[str]] = None) -> bool:
    """Invia un riepilogo delle notizie all'utente specificato."""
    logger.info(f"Preparazione riepilogo per utente {user_id}")

    try:
        if categories is None:
            categories = db.get_user_categories(user_id)

        if not categories:
            categories = ['generale']

        all_news = []

        for category in categories:
            try:
                news = await news_fetcher.get_news(category, limit=3)
                if news:
                    all_news.append(f"📌 *{category.upper()}*:")
                    all_news.append(format_news(news, include_source=True))
            except Exception as e:
                logger.error(f"Errore recupero notizie per categoria {category}: {e}")

        if all_news:
            message = "📰 *RIEPILOGO GIORNALIERO*\n\n" + "\n\n".join(all_news)

            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

            logger.info(f"Riepilogo inviato con successo a {user_id}")
            return True

        logger.info(f"Nessuna notizia disponibile per il riepilogo a {user_id}")
        return False

    except Exception as e:
        logger.error(f"Errore nell'invio riepilogo a {user_id}: {e}", exc_info=True)
        return False