from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import TOKEN, Config
from handlers import commands, auto_send
import asyncio
import logging
from utils.news_fetcher import news_fetcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.logger = logger.getChild('telegram_bot')
        self.application = None
        self.scheduler = None
        self._shutdown_event = asyncio.Event()
        self._background_task = None

    async def run(self):
        """Main entry point for the bot"""
        logger.info("Starting bot initialization")
        self.logger.info("Starting bot initialization")
        try:
            # Initialize application
            self.application = (
                ApplicationBuilder()
                .token(TOKEN)
                .post_init(self._on_application_ready)
                .build()
            )

            # Initialize scheduler with explicit options
            self.scheduler = AsyncIOScheduler(
                timezone="UTC",
                job_defaults={
                    'misfire_grace_time': 60,
                    'coalesce': True,
                    'max_instances': 1
                }
            )

            # Register handlers
            self._register_handlers()

            # Initialize news fetcher
            await news_fetcher.initialize()

            # Start the bot
            logger.info("Starting bot polling")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            # Start background tasks
            self._background_task = asyncio.create_task(self._background_tasks())

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except asyncio.CancelledError:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.critical(f"Bot runtime error: {e}", exc_info=True)
            raise
        finally:
            await self._shutdown()

    async def _on_application_ready(self, app):
        """Configurazione garantita dello scheduler"""
        try:
            # 1. Inizializza lo scheduler con opzioni robuste
            self.scheduler = AsyncIOScheduler(
                timezone="UTC",
                job_defaults={
                    'misfire_grace_time': 300,
                    'coalesce': True,
                    'max_instances': 1
                }
            )

            # 2. Configura i job PRIMA di avviare
            auto_send.setup_periodic_jobs(self.application, self.scheduler)

            # 3. Avvio esplicito con controllo
            self.scheduler.start()
            logger.info(f"🚀 Scheduler avviato con {len(self.scheduler.get_jobs())} job attivi")

            # 4. Verifica iniziale
            for job in self.scheduler.get_jobs():
                logger.info(f"Job {job.id} - Prossima esecuzione: {job.next_run_time}")

        except Exception as e:
            logger.critical(f"CRITICAL: Scheduler failed - {e}", exc_info=True)
            raise

    async def _background_tasks(self):
        """Task di monitoraggio continuo"""
        while not self._shutdown_event.is_set():
            try:
                active_jobs = self.scheduler.get_jobs()
                logger.info(f"🔍 Scheduler Status - Jobs: {len(active_jobs)}")

                if not active_jobs:
                    logger.warning("⚠️ Nessun job attivo! Re-inizializzo...")
                    auto_send.setup_periodic_jobs(self.application, self.scheduler)

                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Background task error: {e}")

    def _register_handlers(self):
        """Register all command handlers"""
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
            CommandHandler('subscribegroup', commands.subscribe_group),
            CommandHandler('group_start', commands.group_start),
            CommandHandler('group_settings', commands.group_settings),
            CommandHandler('admin_stats', commands.admin_stats),
            CommandHandler('test_send', auto_send.test_send),
            CallbackQueryHandler(commands.group_toggle_callback, pattern='^group_toggle:'),
            CallbackQueryHandler(commands.handle_preferences, pattern='^pref_'),
            CallbackQueryHandler(commands.handle_frequency, pattern='^freq_'),
            CommandHandler('test_auto_send', self._test_auto_send)  # New test command
        ]

        for handler in handlers:
            self.application.add_handler(handler)

    async def _test_auto_send(self, update, context):
        """Test command for auto-send functionality"""
        try:
            await update.message.reply_text("Starting auto-send test...")
            result = await auto_send.send_news_to_subscribers(
                context.bot,
                'generale',
                force_update=True
            )
            await update.message.reply_text(f"Auto-send test completed. Sent to {result} users.")
        except Exception as e:
            logger.error(f"Auto-send test failed: {e}")
            await update.message.reply_text(f"Error during test: {e}")

    async def _shutdown(self):
        """Cleanup tasks and shutdown the bot"""
        logger.info("Starting shutdown sequence")

        try:
            # Signal background tasks to stop
            self._shutdown_event.set()

            # Cancel background task
            if self._background_task:
                self._background_task.cancel()
                try:
                    await self._background_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error waiting for background task: {e}")

            # Shutdown scheduler if running
            if self.scheduler and self.scheduler.running:
                logger.info("Stopping scheduler")
                self.scheduler.shutdown(wait=False)

            # Close news fetcher
            logger.info("Closing news fetcher")
            await news_fetcher.close()

            # Shutdown application if running
            if self.application and self.application.running:
                logger.info("Shutting down application")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

        except Exception as e:
            logger.error(f"Shutdown error: {e}")
        finally:
            logger.info("Shutdown completed")


async def main():
    """Entry point that creates and runs the bot"""
    bot = TelegramBot()
    await bot.run()


if __name__ == '__main__':
    try:
        # Create a new event loop for the main thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the bot
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
    finally:
        # Ensure all async resources are closed
        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()