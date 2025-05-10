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
    """Configura i job con intervalli più appropriati e garantisce l'esecuzione"""
    logger.info("🔄 Configurazione job periodici")

    try:
        # Prima rimuovi eventuali job esistenti
        scheduler.remove_all_jobs()

        # Definisci gli intervalli per ogni categoria
        # Le notizie verranno inviate a questi intervalli:
        intervals = {
            # Notizie generali - 4 volte al giorno (ogni 6 ore)
            'generale': {'hours': 6, 'first_run': True},
            
            # Notizie tech - 2 volte al giorno (ogni 12 ore)
            'tech': {'hours': 12, 'first_run': True},
            
            # Notizie gaming - 1 volta al giorno
            'ps5': {'hours': 24, 'first_run': True},
            'xbox': {'hours': 24, 'first_run': True},
            'switch': {'hours': 24, 'first_run': True},
            'pc': {'hours': 24, 'first_run': True},
        }

        # Orari approssimativi di invio per categoria:
        # generale: 00:00, 06:00, 12:00, 18:00
        # tech: 00:00, 12:00
        # gaming: una volta al giorno alle 12:00 (con offset di 30 secondi tra categorie)

        # Aggiungi i job con offset per evitare sovraccarichi
        offset = 0
        for category, config in intervals.items():
            try:
                # Calcola il prossimo orario di esecuzione
                next_run = datetime.now()
                if config['first_run']:
                    # Allinea l'orario al prossimo intervallo completo
                    hours_until_next = config['hours'] - (next_run.hour % config['hours'])
                    next_run = next_run.replace(minute=0, second=0, microsecond=0) + timedelta(hours=hours_until_next)
                    # Aggiungi offset per evitare esecuzioni simultanee
                    next_run += timedelta(seconds=offset)

                job = scheduler.add_job(
                    send_news_to_subscribers,
                    'interval',
                    hours=config['hours'],
                    args=[application.bot, category, False],
                    id=f'autosend_{category}',
                    next_run_time=next_run,
                    replace_existing=True,
                    misfire_grace_time=3600
                )
                
                # Log job configuration
                logger.info(f"Job {job.id} configurato - Intervallo: {config['hours']} ore - Prossimo invio: {next_run}")

                # Aggiungi un offset per distribuire i job
                offset += 30  # 30 secondi di offset tra i job

            except Exception as e:
                logger.error(f"Errore configurazione job per {category}: {e}")

        # Aggiungi job di reset cache (ogni 12 ore - 00:00 e 12:00)
        try:
            next_cache_reset = datetime.now().replace(minute=0, second=0, microsecond=0)
            hours_until_next = 12 - (next_cache_reset.hour % 12)
            next_cache_reset += timedelta(hours=hours_until_next)
            
            cache_job = scheduler.add_job(
                reset_cache,
                'interval',
                hours=12,
                id='reset_cache',
                replace_existing=True,
                next_run_time=next_cache_reset
            )
            logger.info(f"Job reset cache configurato - Prossima esecuzione: {next_cache_reset}")
        except Exception as e:
            logger.error(f"Errore configurazione job reset cache: {e}")

        # Aggiungi job di pulizia utenti inattivi (una volta al giorno alle 03:00)
        try:
            next_cleanup = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)
            if next_cleanup < datetime.now():
                next_cleanup += timedelta(days=1)
                
            cleanup_job = scheduler.add_job(
                cleanup_inactive_users,
                'interval',
                hours=24,
                args=[application.bot],
                id='cleanup_inactive',
                replace_existing=True,
                next_run_time=next_cleanup
            )
            logger.info(f"Job pulizia utenti configurato - Prossima esecuzione: {next_cleanup}")
        except Exception as e:
            logger.error(f"Errore configurazione job pulizia: {e}")

        # Configurazione scheduler
        scheduler.configure(
            {
                'apscheduler.job_defaults.coalesce': True,
                'apscheduler.job_defaults.max_instances': 1,
                'apscheduler.timezone': 'UTC'
            }
        )

        # Log riepilogo job configurati
        jobs = scheduler.get_jobs()
        logger.info(f"✅ {len(jobs)} job configurati correttamente")
        for job in jobs:
            try:
                if hasattr(job, 'next_run_time') and job.next_run_time:
                    logger.info(f"Job {job.id} - Prossima esecuzione: {job.next_run_time}")
                else:
                    logger.info(f"Job {job.id} - Prossima esecuzione: non definita")
            except Exception as e:
                logger.error(f"Errore logging job {job.id}: {e}")

    except Exception as e:
        logger.error(f"Errore grave in setup_periodic_jobs: {e}", exc_info=True)
        raise


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