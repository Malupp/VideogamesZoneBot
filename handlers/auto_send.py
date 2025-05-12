import asyncio

from apscheduler.schedulers import SchedulerAlreadyRunningError
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from utils.news_fetcher import news_fetcher
from utils.helpers import format_news
from database.db import Database
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)
db = Database()

# Cache per le notizie inviate
last_sent_news: Dict[str, List[Tuple[str, str, str]]] = {}


async def send_news_to_subscribers(bot, category: str, force_update: bool = False) -> int:
    """Versione migliorata e più robusta per l'invio di notizie"""
    try:
        logger.info(f"==== INIZIA SEND_NEWS_TO_SUBSCRIBERS PER {category} ====")
        logger.info(f"Force update: {force_update}")

        if not hasattr(bot, 'get_me'):
            logger.error("Bot instance non valida")
            return 0

        # Verifica bot
        try:
            bot_info = await bot.get_me()
            logger.info(f"Bot valido: {bot_info.username}")
        except Exception as e:
            logger.error(f"Errore verifica bot: {e}")
            return 0

        # Ottenimento dei subscribers
        subscribers = db.get_subscribers(category)
        logger.info(f"Trovati {len(subscribers)} iscritti per {category}")
        if not subscribers:
            logger.info(f"Nessun iscritto per {category}, skip invio")
            return 0

        # Log degli ID dei subscribers in modo sicuro
        subscriber_ids = list(subscribers.keys())
        preview_ids = subscriber_ids[:5]
        logger.info(f"Subscriber IDs: {preview_ids}{'... e altri' if len(subscriber_ids) > 5 else ''}")

        # Recupera le notizie
        try:
            news = await news_fetcher.get_news(category, limit=5)
            if not news:
                logger.info(f"Nessuna notizia trovata per {category}")
                return 0
        except Exception as e:
            logger.error(f"Errore nel recupero notizie per {category}: {e}")
            return 0

        # Verifica se le notizie sono già state inviate recentemente (cache)
        if not force_update and category in last_sent_news:
            # Confronta titoli per evitare duplicati
            old_titles = set(item[0] for item in last_sent_news[category])
            new_titles = set(item[0] for item in news)

            if old_titles == new_titles:
                logger.info(f"Le stesse notizie per {category} sono già state inviate di recente, salto")
                return 0

        # Aggiorna la cache
        last_sent_news[category] = news

        # Formatta il messaggio
        try:
            message = f"📰 *Ultime notizie {category.upper()}*\n\n{format_news(news)}"
        except Exception as e:
            logger.error(f"Errore nella formattazione del messaggio per {category}: {e}")
            message = f"📰 *Ultime notizie {category.upper()}*\n\n"
            for i, (title, url, source) in enumerate(news, 1):
                message += f"{i}. {title} ({source})\n{url}\n\n"

        # Invia a tutti gli iscritti
        success_count = 0
        error_count = 0
        for user_id in subscriber_ids:  # Usa la lista di ID invece del dizionario direttamente
            try:
                # Log dettagliato prima dell'invio
                logger.debug(f"Invio notizie {category} a utente {user_id}")

                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                success_count += 1
                await asyncio.sleep(0.2)  # Rate limiting più rilassato

            except (BadRequest, Forbidden) as e:
                logger.warning(f"Impossibile inviare a {user_id}: {e}")
                db.unsubscribe(user_id, category)  # Rimuovi iscritti non validi
                error_count += 1

            except Exception as e:
                logger.error(f"Errore invio a {user_id}: {e}")
                error_count += 1
                # Continua con gli altri utenti
                await asyncio.sleep(1)  # Pausa più lunga in caso di errore

        # Aggiorna le statistiche nel database
        try:
            db.increment_news_sent(success_count)
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento delle statistiche: {e}")

        logger.info(f"Inviate notizie {category} a {success_count}/{len(subscriber_ids)} utenti (errori: {error_count})")
        return success_count

    except Exception as e:
        logger.error(f"Errore grave in send_news_to_subscribers: {e}", exc_info=True)
        return 0


def setup_periodic_jobs(application, scheduler):
    """Configura i job periodici in modo sicuro"""
    try:
        # Verifica se lo scheduler è già in esecuzione
        if scheduler.running:
            logger.info("Scheduler già avviato, skip riconfigurazione")
            return

        logger.info("Configurazione job periodici (senza emoticon)")

        # Rimuovi tutti i job esistenti
        scheduler.remove_all_jobs()

        # Configura i nuovi job
        categories = {
            'generale': timedelta(hours=6),
            'tech': timedelta(hours=12),
            'ps5': timedelta(days=1),
            'xbox': timedelta(days=1),
            'switch': timedelta(days=1),
            'pc': timedelta(days=1)
        }

        for category, interval in categories.items():
            scheduler.add_job(
                send_news_to_subscribers,
                'interval',
                args=[application.bot, category],
                hours=interval.total_seconds() // 3600,
                id=f"autosend_{category}",
                next_run_time=datetime.now() + timedelta(minutes=1))
            logger.info(f"Job {category} configurato - Intervallo: {interval}")

        # Job per la pulizia
        scheduler.add_job(
            reset_news_cache,
            'cron',
            hour=0,
            id="reset_cache"
        )

        scheduler.add_job(
            cleanup_inactive_users,
            'cron',
            hour=3,
            id="cleanup_users"
        )

    except SchedulerAlreadyRunningError:
        logger.warning("Scheduler già in esecuzione, skip configurazione")
    except Exception as e:
        logger.error(f"Errore configurazione job: {e}", exc_info=True)


async def reset_news_cache():
    """Resetta la cache delle news a mezzanotte"""
    try:
        from utils.news_fetcher import news_fetcher

        logger.info("🔄 Resetting news cache...")
        news_fetcher.cache.clear()
        news_fetcher.last_fetch.clear()
        logger.info("✅ News cache reset completato")

    except Exception as e:
        logger.error(f"Errore nel reset della cache: {e}")


async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando di test per verificare l'invio"""
    try:
        await update.message.reply_text("⚙️ Avvio test invio notizie...")

        # Log dettagliato
        logger.info(f"Test invio avviato da utente {update.effective_user.id}")

        # Forza l'invio per la categoria generale
        result = await send_news_to_subscribers(context.bot, 'generale', True)

        await update.message.reply_text(f"✅ Test completato! Inviato a {result} utenti")
        logger.info(f"Test invio completato: {result} messaggi inviati")

    except Exception as e:
        logger.error(f"Errore test_send: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Errore durante il test: {str(e)}")


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
                await asyncio.sleep(0.2)  # Rate limiting

            except (Forbidden, BadRequest):
                db.remove_user(user_id)
                removed += 1
                logger.info(f"Rimosso utente {user_id} (chat non disponibile)")

            except Exception as e:
                logger.error(f"Errore durante la pulizia per utente {user_id}: {e}")

        logger.info(f"Pulizia completata, elaborati {removed} utenti inattivi")

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