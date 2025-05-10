import asyncio

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
    """Versione semplificata e più robusta"""
    try:
        logger.info(f"Inizio invio notizie per {category}")

        # Ottieni gli iscritti
        subscribers = db.get_subscribers(category)
        if not subscribers:
            logger.info(f"Nessun iscritto per {category}")
            return 0

        # Recupera le notizie
        news = await news_fetcher.get_news(category, limit=5)
        if not news:
            logger.info(f"Nessuna notizia trovata per {category}")
            return 0

        # Formatta il messaggio
        message = f"📰 *Ultime notizie {category.upper()}*\n\n{format_news(news)}"

        # Invia a tutti gli iscritti
        success_count = 0
        for user_id in subscribers:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                success_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except (BadRequest, Forbidden) as e:
                logger.warning(f"Impossibile inviare a {user_id}: {e}")
                db.unsubscribe(user_id, category)  # Rimuovi iscritti non validi
            except Exception as e:
                logger.error(f"Errore invio a {user_id}: {e}")

        logger.info(f"Inviate notizie {category} a {success_count}/{len(subscribers)} utenti")
        return success_count

    except Exception as e:
        logger.error(f"Errore grave in send_news_to_subscribers: {e}", exc_info=True)
        return 0


def setup_periodic_jobs(application, scheduler):
    """Configura i job con intervalli di test e garantisce l'esecuzione continua"""
    logger.info("🔄 Configurazione job periodici (WEBHOOK MODE)")

    # Rimuovi job esistenti e riparti da zero
    scheduler.remove_all_jobs()

    intervals = {
        'generale': {'interval': 1800, 'first_run': True},  # 30 minuti
        'tech': {'interval': 3600, 'first_run': True},  # 1 ora
        'ps5': {'interval': 3600, 'first_run': True},
        'xbox': {'interval': 3600, 'first_run': True},
        'switch': {'interval': 3600, 'first_run': True},
        'pc': {'interval': 3600, 'first_run': True},
    }

    for category, config in intervals.items():
        scheduler.add_job(
            send_news_to_subscribers,
            'interval',
            seconds=config['interval'],
            args=[application.bot, category],
            id=f'autosend_{category}',
            next_run_time=datetime.now() if config['first_run'] else None,
            replace_existing=True,
            misfire_grace_time=3600
        )

    logger.info(f"✅ Job attivi: {[j.id for j in scheduler.get_jobs()]}")

async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando di test per verificare l'invio"""
    try:
        await update.message.reply_text("Avvio test invio notizie...")
        result = await send_news_to_subscribers(context.bot, 'generale', True)
        await update.message.reply_text(f"Test completato! Inviato a {result} utenti")
    except Exception as e:
        logger.error(f"Errore test_send: {e}")
        await update.message.reply_text(f"Errore durante il test: {str(e)}")


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