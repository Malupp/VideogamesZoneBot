import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Configurazione feed
    NEWS_UPDATE_INTERVAL = int(os.getenv('NEWS_UPDATE_INTERVAL', 60))  # minuti
    TECH_UPDATE_INTERVAL = int(os.getenv('TECH_UPDATE_INTERVAL', 120))

# Inserisci il tuo token qui
TOKEN = '7927920308:AAHS--egXHdQNvAMRH2brUHBYziDgd4jvRY'

# Chat ID per inviare le notizie in automatico
CHAT_ID = '-1001036269713'