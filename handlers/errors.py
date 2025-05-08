# handlers/errors.py
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log error and send a message to the user."""
    logger.error("Errore durante l'aggiornamento %s: %s", update, context.error, exc_info=True)

    if isinstance(update, Update) and update.message:
        error_msg = "Si è verificato un errore. Riprova più tardi."
        if "Notizie non trovate" in str(context.error):
            error_msg = "🔍 Nessuna notizia trovata per la tua richiesta."

        await update.message.reply_text(error_msg)