# utils/logger.py
import logging
from logging.handlers import RotatingFileHandler


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Formattatore
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Handler per file (rotazione)
    file_handler = RotatingFileHandler(
        'bot.log', maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler per console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger