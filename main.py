from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from telegram import Update
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from config import TOKEN, Config
from handlers import commands, auto_send, errors
import asyncio
import logging
import os
from datetime import datetime
from utils.news_fetcher import news_fetcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import db

# Configure loggingg
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Inizializza FastAPI
app = FastAPI()


class TelegramBot:
    def __init__(self):
        self.logger = logger.getChild('telegram_bot')
        self.application = None
        self.scheduler = None  # Inizializzato qui ma configurato dopo
        self._shutdown_event = asyncio.Event()
        self.initialization_complete = False

    async def initialize(self):
        """Inizializza il bot senza avviarlo"""
        if self.initialization_complete:
            return

        self.logger.info("Inizializzazione bot in corso...")

        try:
            # 1. Prima inizializza l'applicazione
            self.application = (
                ApplicationBuilder()
                .token(TOKEN)
                .build()
            )

            # 2. Configura lo scheduler con event loop corrente
            self.scheduler = AsyncIOScheduler(
                timezone="UTC",
                job_defaults={
                    'misfire_grace_time': 3600,
                    'coalesce': True,
                    'max_instances': 1
                }
            )
            self.scheduler.configure(event_loop=asyncio.get_event_loop())

            # 3. Assegna lo scheduler all'applicazione
            self.application.scheduler = self.scheduler

            # Registra gli handler
            self._register_handlers()

            # Inizializza news fetcher
            await news_fetcher.initialize()

            # Inizializza l'applicazione
            await self.application.initialize()

            # Configura lo scheduler
            auto_send.setup_periodic_jobs(self.application, self.scheduler)

            # Avvia lo scheduler
            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info(f"🚀 Scheduler avviato con {len(self.scheduler.get_jobs())} job attivi")
                # Log dei job configurati
                for job in self.scheduler.get_jobs():
                    self.logger.info(f"Job {job.id} - Prossima esecuzione: {job.next_run_time}")

            self.initialization_complete = True
            self.logger.info("Inizializzazione bot completata")


        except Exception as e:
            self.logger.critical(f"Errore inizializzazione bot: {e}", exc_info=True)
            # Riavvia dopo un delay
            await asyncio.sleep(5)
            await self.initialize()

    def _register_handlers(self):
        """Registra tutti gli handler dei comandi"""
        handlers = [
            CommandHandler('start', commands.start),
            CommandHandler('help', commands.help),
            CommandHandler('news', commands.news),
            CommandHandler('sommario', commands.sommario),
            CommandHandler('dettaglio', commands.dettaglio),
            CommandHandler('preferenze', commands.preferenze),
            CommandHandler('getchatid', commands.get_chat_id),
            CommandHandler('ps5', commands.ps5),
            CommandHandler('xbox', commands.xbox),
            CommandHandler('switch', commands.switch),
            CommandHandler('pc', commands.pc),
            CommandHandler('tech', commands.tech),
            CommandHandler('news5', commands.news_5),
            CommandHandler('news10', commands.news_10),
            CommandHandler('crypto', commands.crypto),
            CommandHandler('ia', commands.ai),
            CommandHandler('cerca', commands.search),
            CommandHandler('search', commands.search),
            # New commands
            CommandHandler('releases', commands.releases),
            CommandHandler('deals', commands.deals),
            CommandHandler('top', commands.top_news),
            CommandHandler('filter', commands.filter_news),
            CommandHandler('digest', commands.daily_digest),
            # Group commands
            CommandHandler('subscribegroup', commands.subscribe_group),
            CommandHandler('group_start', commands.group_start),
            CommandHandler('group_settings', commands.group_settings),
            # Admin commands
            CommandHandler('admin_stats', commands.admin_stats),
            CommandHandler('debug_scheduler', commands.debug_scheduler),
            CommandHandler('test_send', auto_send.test_send),
            CommandHandler('debug_db', commands.debug_database),
            # Callbacks
            CallbackQueryHandler(commands.group_toggle_callback, pattern='^group_toggle:'),
            CallbackQueryHandler(commands.handle_preferences, pattern='^pref_'),
            CallbackQueryHandler(commands.handle_frequency, pattern='^freq_'),
            CallbackQueryHandler(commands.handle_filter_callback, pattern='^filter_'),
        ]

        for handler in handlers:
            self.application.add_handler(handler)

        # Aggiungi l'error handler
        self.application.add_error_handler(errors.error_handler)

    async def check_scheduler(self):
        """Controlla e ripristina lo scheduler se necessario"""
        try:
            active_jobs = self.scheduler.get_jobs()
            self.logger.info(f"🔍 Stato Scheduler - Jobs attivi: {len(active_jobs)}")

            if not active_jobs:
                self.logger.warning("⚠️ Nessun job attivo! Re-inizializzo...")
                auto_send.setup_periodic_jobs(self.application, self.scheduler)

                # Forza l'esecuzione immediata per test
                for job in self.scheduler.get_jobs():
                    job.modify(next_run_time=datetime.now())
                    self.logger.info(f"Job {job.id} - Prossima esecuzione forzata: {job.next_run_time}")

        except Exception as e:
            self.logger.error(f"Errore verifica scheduler: {e}")

    async def shutdown(self):
        """Pulisce e spegne il bot"""
        self.logger.info("Avvio sequenza di spegnimento")

        try:
            # Segnala l'arresto
            self._shutdown_event.set()

            # Arresta lo scheduler
            if self.scheduler and self.scheduler.running:
                self.logger.info("Arresto scheduler")
                self.scheduler.shutdown(wait=False)

            # Chiudi news fetcher
            self.logger.info("Chiusura news fetcher")
            await news_fetcher.close()

            # Arresta l'applicazione
            if self.application:
                self.logger.info("Arresto applicazione")
                await self.application.shutdown()

        except Exception as e:
            self.logger.error(f"Errore durante lo spegnimento: {e}")
        finally:
            self.logger.info("Spegnimento completato")


# Inizializza il bot come variabile globale
bot_app = TelegramBot()


@app.on_event("startup")
async def startup_event():
    """Evento di avvio di FastAPI"""
    global bot_app
    try:
        await bot_app.initialize()
        logger.info("Server FastAPI avviato e bot inizializzato")
        asyncio.create_task(scheduler_monitor())
    except Exception as e:
        logger.critical(f"Errore durante l'avvio: {e}")
        raise


async def scheduler_monitor():
    """Monitora lo scheduler in background"""
    while True:
        await bot_app.check_scheduler()
        await asyncio.sleep(300)  # Controlla ogni 5 minuti


@app.on_event("shutdown")
async def shutdown_event():
    global bot_app
    if bot_app:
        logger.info("Inizio shutdown...")
        try:
            await asyncio.wait_for(bot_app.shutdown(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Timeout durante lo shutdown")

@app.post("/webhook")
async def webhook(request: Request):
    """Gestisce gli aggiornamenti webhook di Telegram"""
    global bot_app

    try:
        # Assicurati che il bot sia inizializzato
        if not bot_app.initialization_complete:
            await bot_app.initialize()

        # Leggi l'aggiornamento JSON
        update_data = await request.json()

        # Processa l'aggiornamento
        update = Update.de_json(update_data, bot_app.application.bot)
        await bot_app.application.process_update(update)

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Errore nel webhook: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.get("/")
async def health_check():
    """Endpoint per verificare lo stato del bot"""
    global bot_app

    scheduler_status = "running" if bot_app and bot_app.scheduler and bot_app.scheduler.running else "not running"
    jobs = len(bot_app.scheduler.get_jobs()) if bot_app and bot_app.scheduler else 0

    return {
        "status": "ok",
        "scheduler": scheduler_status,
        "active_jobs": jobs,
        "bot_initialized": bot_app.initialization_complete if bot_app else False
    }

@app.get("/status")
async def status(self):
    return {
        "scheduler": bot_app.scheduler.state if bot_app.scheduler else "off",
        "last_news": {k: len(v) for k,v in news_fetcher.cache.items()},
        "subscribers": db.Database.get_subscriber_counts(self)
    }

@app.get("/subscriber_counts")
async def get_subscriber_counts(self):
    return db.Database.get_subscriber_counts(self)


@app.get("/set_webhook")
async def set_webhook():
    """Imposta manualmente il webhook"""
    global bot_app

    if not bot_app.initialization_complete:
        await bot_app.initialize()

    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot_app.application.bot.set_webhook(webhook_url)

    return {
        "status": "ok",
        "webhook_url": webhook_url
    }


@app.get("/force_jobs")
async def force_jobs():
    """Forza l'esecuzione di tutti i job schedulati"""
    global bot_app

    if not bot_app.initialization_complete:
        await bot_app.initialize()

    job_count = 0
    for job in bot_app.scheduler.get_jobs():
        job.modify(next_run_time=datetime.now())
        job_count += 1

    return {
        "status": "ok",
        "forced_jobs": job_count
    }


def run():
    """Punto di ingresso per l'avvio da riga di comando"""
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")


def check_config():
    required = ['TOKEN', 'ADMIN_IDS']
    for var in required:
        if not hasattr(Config, var):
            raise ValueError(f"Config.{var} mancante nel file config.py")

if __name__ == "__main__":
    check_config()
    run()