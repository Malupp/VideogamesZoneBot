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
import sys
import io
from datetime import datetime
from utils.news_fetcher import news_fetcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import db

# Configura sys.stdout per supportare Unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(stream=sys.stdout),  # Usa stdout configurato
        logging.FileHandler('bot.log', encoding='utf-8')  # File con encoding UTF-8
    ]
)
logger = logging.getLogger(__name__)

# Inizializza FastAPI
app = FastAPI()


class TelegramBot:
    def __init__(self):
        self.post_init = self._post_init  # Assegna il metodo post_init
        self.logger = logger.getChild('telegram_bot')
        self.application = None
        self.scheduler = None
        self._shutdown_event = asyncio.Event()
        self.initialization_complete = False

    async def _post_init(self, application):
        """Callback dopo l'inizializzazione dell'Application"""
        self.application = application
        self.logger.info("Application initialized in post_init")

    async def initialize(self):
        """Versione corretta del metodo initialize"""
        if self.initialization_complete:
            return

        retries = 3
        for attempt in range(retries):
            try:
                # 1. Inizializza news_fetcher
                await news_fetcher.initialize()

                # 2. Crea l'applicazione Telegram con post_init
                self.application = (
                    ApplicationBuilder()
                    .token(TOKEN)
                    .post_init(self.post_init)
                    .build()
                )

                # 3. Configura scheduler
                self.scheduler = AsyncIOScheduler(timezone="UTC")
                self.scheduler.start()

                # Assegna lo scheduler all'application
                if self.application:
                    self.application.scheduler = self.scheduler

                # 4. Registra handlers
                self._register_handlers()

                # 5. Configura job periodici
                auto_send.setup_periodic_jobs(self.application, self.scheduler)

                # 6. Inizializza l'application
                await self.application.initialize()  # AGGIUNTA CRUCIALE

                self.initialization_complete = True
                logger.info("✅ Bot inizializzato correttamente")
                return

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(5)

    def _register_handlers(self):
        """Registra tutti gli handler dei comandi"""
        handlers = [
            CommandHandler('start', commands.start),
            CommandHandler('help', commands.help),
            CommandHandler('news', commands.news),
            CommandHandler('lingua', commands.lingua),  # NEW
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
            CommandHandler('becomeadmin', commands.becomeadmin),  # NEW
            # Callbacks
            CallbackQueryHandler(commands.group_toggle_callback, pattern='^group_toggle:'),
            CallbackQueryHandler(commands.handle_preferences, pattern='^pref_'),
            CallbackQueryHandler(commands.handle_frequency, pattern='^freq_'),
            CallbackQueryHandler(commands.handle_filter_callback, pattern='^filter_'),
            CallbackQueryHandler(commands.handle_news_buttons, pattern='^news_'),  # NEW
            CallbackQueryHandler(commands.handle_set_lang, pattern='^set_lang_'),  # NEW
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

# Sostituisci TUTTA la parte finale di main.py a partire dalla creazione dell'app FastAPI

from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce gli eventi di startup e shutdown dell'applicazione"""
    # Parte di startup
    logger.info("Starting up...")
    global bot_app

    try:
        await bot_app.initialize()
        logger.info("Bot initialized successfully")

        # Avvia il task di monitoraggio dello scheduler
        asyncio.create_task(scheduler_monitor())

        yield  # L'applicazione è ora in esecuzione

    except Exception as e:
        logger.critical(f"Startup failed: {e}")
        raise

    finally:
        # Parte di shutdown
        logger.info("Shutting down...")
        try:
            if bot_app:
                await bot_app.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Crea l'app FastAPI con il gestore di lifespan
app = FastAPI(lifespan=lifespan)


async def scheduler_monitor():
    """Monitora lo scheduler in background"""
    while True:
        await bot_app.check_scheduler()
        await asyncio.sleep(300)  # Controlla ogni 5 minuti


async def shutdown_event():
    global bot_app
    if bot_app:
        logger.info("Inizio shutdown...")
        try:
            await asyncio.wait_for(bot_app.shutdown(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Timeout durante lo shutdown")

@app.get("/init_bot")
async def init_bot():
    """Endpoint per forzare l'inizializzazione"""
    global bot_app
    try:
        if not bot_app.initialization_complete:
            await bot_app.initialize()
            return {"status": "initialized"}
        return {"status": "already_initialized"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/webhook")
async def webhook(request: Request):
    """Gestisce gli aggiornamenti webhook di Telegram"""
    global bot_app
    try:
        if not bot_app.initialization_complete or not bot_app.application:
            logger.error("Bot non inizializzato quando arrivato webhook")
            return JSONResponse(
                content={"status": "error", "message": "Bot not initialized"},
                status_code=503
            )

        update_data = await request.json()
        update = Update.de_json(update_data, bot_app.application.bot)

        # Verifica ulteriore che l'application sia pronta
        if not bot_app.application.updater:
            await bot_app.application.initialize()

        await bot_app.application.process_update(update)
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )


@app.get("/")
async def health_check():
    """Endpoint per verificare lo stato del bot"""
    global bot_app

    status = {
        "status": "ok" if bot_app.initialization_complete else "initializing",
        "timestamp": datetime.now().isoformat()
    }

    if bot_app.scheduler:
        status.update({
            "scheduler": "running" if bot_app.scheduler.running else "stopped",
            "active_jobs": len(bot_app.scheduler.get_jobs())
        })

    return status

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
    # Configura Uvicorn con logging
    config = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        log_level="info",
        server_header=False,
        timeout_keep_alive=60
    )

    server = uvicorn.Server(config)

    try:
        # Avvia il server con gestione degli errori
        asyncio.run(server.serve())
    except Exception as e:
        logger.critical(f"Server failed: {e}")
    finally:
        logger.info("Server stopped")

def check_config():
    required = ['TOKEN', 'ADMIN_IDS']
    for var in required:
        if not hasattr(Config, var):
            raise ValueError(f"Config.{var} mancante nel file config.py")

if __name__ == "__main__":
    check_config()
    run()