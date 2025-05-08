import logging
import sys

def setup_logger(name=__name__):
    """Configura un logger con output su console e file"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Formattatore comune
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Handler per console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Handler per file
    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(formatter)

    # Aggiungi gli handler
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Logger globale
logger = setup_logger('bot_main')