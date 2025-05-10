from telegram import Update
from telegram.ext import Application, ContextTypes
from main import TelegramBot
import os


async def handle_webhook(request):
    """Handle incoming Telegram updates by putting them into the `update_queue`"""
    bot = TelegramBot()
    await bot.application.initialize()

    # Get the update from the request
    update_data = await request.json()
    update = Update.de_json(update_data, bot.application.bot)

    # Put the update into the update queue
    await bot.application.update_queue.put(update)

    return {"status": "ok"}


async def setup_webhook():
    """Setup webhook endpoint"""
    bot = TelegramBot()
    await bot.run()