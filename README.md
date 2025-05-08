# 📰 Bot Telegram Notizie Videogiochi & Tech

Questo bot Telegram invia **notizie aggiornate** su videogiochi e tecnologia. Gli utenti possono:

- ricevere aggiornamenti per categoria
- cercare notizie per parole chiave
- impostare preferenze personalizzate
- ottenere sommari o dettagli di singole notizie

## ⚙️ Funzionalità principali

- Invio automatico di notizie ogni giorno
- Notizie per categoria (PS5, Xbox, PC, Switch, Tech, IA, Crypto)
- Ricerca per parola chiave
- Sistema di preferenze utente
- Sommario e dettaglio notizie
- Pianificazione automatica con APScheduler

## 💬 Comandi disponibili

start - Avvia il bot
help - Mostra tutti i comandi
news - Notizie [categoria]
sommario - Sommario notizie
dettaglio - Dettaglio notizia
cerca - Cerca notizie
preferenze - Imposta preferenze

ps5 - Notizie PS5
xbox - Notizie Xbox
switch - Notizie Switch
pc - Notizie PC

tech - Notizie tecnologia
ia - Notizie intelligenza artificiale
crypto - Notizie criptovalute

news5 - 5 notizie
news10 - 10 notizie


## 🛠️ Tecnologie usate

- Python 3.12  
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)  
- aiohttp  
- APScheduler  
- SQLite

## 🚀 Avvio del bot

1. Clona la repo:

```bash
git clone https://github.com/tuo-utente/bot-telegram-news.git
cd bot-telegram-news
```

2. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

3. Crea un file .env con il tuo token Telegram:
```bash
BOT_TOKEN=il_tuo_token
```
4. Avvia il bot:
```bash
python main.py
```
