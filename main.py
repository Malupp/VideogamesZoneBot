from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import TOKEN
from handlers import commands, auto_send
import asyncio
import logging
from utils.news_fetcher import news_fetcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.application = None
        self.scheduler = None
        self._shutdown_event = asyncio.Event()

    async def run(self):
        """Main entry point for the bot"""
        print("[DEBUG] Starting bot initialization")

        try:
            # Initialize components
            self.application = ApplicationBuilder().token(TOKEN).build()
            self.scheduler = AsyncIOScheduler()

            # Setup components
            self._register_handlers()
            auto_send.setup_periodic_jobs(self.application, self.scheduler)

            # Start scheduler before polling
            self.scheduler.start()
            print("[INFO] Scheduler started")

            # Start background tasks
            asyncio.create_task(self._background_tasks())

            print("[INFO] Bot is running")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except asyncio.CancelledError:
            print("[INFO] Received shutdown signal")
        except Exception as e:
            logger.error(f"Bot runtime error: {e}", exc_info=True)
            print(f"[CRITICAL] Bot crashed: {e}")
        finally:
            await self._shutdown()

    async def _background_tasks(self):
        """Handle background tasks"""
        try:
            # Initialize and refresh feeds
            await news_fetcher.initialize()

            # Keep the task running until shutdown
            while not self._shutdown_event.is_set():
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Background task error: {e}")
            self._shutdown_event.set()

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
            CallbackQueryHandler(commands.handle_preferences, pattern='^pref_'),
            CallbackQueryHandler(commands.handle_frequency, pattern='^freq_')
        ]

        for handler in handlers:
            self.application.add_handler(handler)

    async def _shutdown(self):
        """Cleanup tasks and shutdown the bot"""
        print("[DEBUG] Starting shutdown sequence")

        try:
            # Signal background tasks to stop
            self._shutdown_event.set()

            # Shutdown scheduler if running
            if self.scheduler and self.scheduler.running:
                print("[DEBUG] Stopping scheduler")
                self.scheduler.shutdown(wait=False)

            # Close news fetcher
            print("[DEBUG] Closing news fetcher")
            await news_fetcher.close()

            # Shutdown application if running
            if self.application and self.application.running:
                print("[DEBUG] Shutting down application")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            print(f"[ERROR] Shutdown failed: {e}")
        finally:
            print("[INFO] Shutdown completed")


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
        print("\n[INFO] Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
    finally:
        # Ensure all async resources are closed
        loop.close()