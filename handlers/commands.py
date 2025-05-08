from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import format_news
from utils.news_fetcher import get_news
import config
from utils import logger, news_fetcher
from database import db
from database.db import Database
import logging
from utils.logger import logger

command_logger = logger.getChild('commands')

# Funzione di benvenuto
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione start chiamata.")
    print("Comando /start ricevuto.")  # Aggiungi print per monitorare l'uso del comando
    await update.message.reply_text('Ciao! Scrivi /news per leggere le ultime notizie videoludiche.')


async def preferenze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu per impostare le preferenze"""
    keyboard = [
        [InlineKeyboardButton("🎮 Solo Videogiochi", callback_data='pref_games')],
        [InlineKeyboardButton("💻 Solo Tech", callback_data='pref_tech')],
        [InlineKeyboardButton("🎮+💻 Entrambi", callback_data='pref_both')],
        [InlineKeyboardButton("🔔 Frequenza Alta", callback_data='freq_high')],
        [InlineKeyboardButton("🔕 Frequenza Bassa", callback_data='freq_low')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        '🔧 *Imposta le tue preferenze*:\n\n'
        'Scegli cosa vuoi ricevere e con quale frequenza:',
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la selezione delle preferenze"""
    query = update.callback_query
    await query.answer()

    choice = query.data
    user_id = query.from_user.id

    # Qui dovresti salvare nel database le preferenze
    # Esempio pseudocodice:
    # db.set_user_preference(user_id, preference=choice.replace('pref_', ''))

    if choice == 'pref_games':
        response = "Preferenza impostata: solo videogiochi 🎮"
    elif choice == 'pref_tech':
        response = "Preferenza impostata: solo tech 💻"
    else:  # pref_both
        response = "Preferenza impostata: videogiochi e tech 🎮+💻"

    await query.edit_message_text(text=response)


async def handle_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la frequenza di invio"""
    query = update.callback_query
    await query.answer()

    choice = query.data
    user_id = query.from_user.id

    # Salva la preferenza di frequenza
    # db.set_user_frequency(user_id, frequency=choice.replace('freq_', ''))

    if choice == 'freq_high':
        response = "Frequenza impostata: aggiornamenti frequenti 🔔"
    else:
        response = "Frequenza impostata: aggiornamenti ridotti 🔕"

    await query.edit_message_text(text=response)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi che non sono comandi"""
    text = update.message.text.lower()

    if any(word in text for word in ['ciao', 'salve', 'buongiorno']):
        await update.message.reply_text("Ciao! Scrivi /help per vedere cosa posso fare.")
    elif 'grazie' in text:
        await update.message.reply_text("Di nulla! 😊")
    elif any(word in text for word in ['notizie', 'news', 'novità']):
        await news(update, context)
    else:
        await update.message.reply_text(
            "Non ho capito. Scrivi /help per vedere i comandi disponibili."
        )

async def cerca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cerca notizie per parole chiave"""
    if not context.args:
        await update.message.reply_text("Usa: /cerca <termine>")
        return

    search_term = ' '.join(context.args)
    news = news_fetcher.search_news(search_term)

    if news:
        # Formatta e invia i risultati
        pass
    else:
        await update.message.reply_text("Nessun risultato trovato.")

# Funzione per ottenere le notizie
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione news chiamata.")
    try:
        category = context.args[0].lower() if context.args else 'generale'
        print(f"Categoria richiesta: {category}")

        # Aggiungi await qui per ottenere il risultato della coroutine
        news_list = await news_fetcher.get_news(category)

        print(f"Numero di notizie trovate: {len(news_list)}")

        if news_list:
            msg = format_news(news_list)
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            print("Nessuna notizia trovata.")
            await update.message.reply_text("Nessuna notizia trovata.")

    except Exception as e:
        print(f"Errore durante il fetch delle news: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

# Funzione per ottenere il chat_id del gruppo
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione get_chat_id chiamata.")
    chat_id = update.message.chat.id  # Ottieni il chat_id del gruppo
    print(f"chat_id del gruppo: {chat_id}")  # Stampa il chat_id nel log
    await update.message.reply_text(f"Il chat_id di questo gruppo è: {chat_id}")

# Comandi per le categorie specifiche
async def ps5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione ps5 chiamata.")
    try:
        news_list = await news_fetcher.get_news('ps5')  # Aggiunto await
        if news_list:
            print(f"Notizie per PS5: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            print("Nessuna notizia per PS5.")
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in ps5: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

async def xbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione xbox chiamata.")
    try:
        news_list = await news_fetcher.get_news('xbox')  # Aggiunto await
        if news_list:
            print(f"Notizie per Xbox: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            print("Nessuna notizia per Xbox.")
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in xbox: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione switch chiamata.")
    try:
        news_list = await news_fetcher.get_news('switch')  # Aggiunto await
        if news_list:
            print(f"Notizie per Switch: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            print("Nessuna notizia per Switch.")
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in switch: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

async def pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione pc chiamata.")
    try:
        news_list = await news_fetcher.get_news('pc')  # Aggiunto await
        if news_list:
            print(f"Notizie per PC: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            print("Nessuna notizia per PC.")
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in pc: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

async def tech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione tech chiamata.")
    try:
        news_list = await news_fetcher.get_news('tech')  # Aggiunto await
        if news_list:
            print(f"Notizie per Tech: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            print("Nessuna notizia per Tech.")
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in tech: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

async def news_5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione news_5 chiamata.")
    try:
        news_list = await get_news(limit=5)  # Aggiunto await
        if news_list:
            print(f"Numero di notizie trovate: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in news_5: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

async def news_10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione news_10 chiamata.")
    try:
        news_list = await get_news(limit=10)  # Aggiunto await
        if news_list:
            print(f"Numero di notizie trovate: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in news_10: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

# Variabile globale per memorizzare le ultime notizie inviate per chat
LAST_NEWS = {}


async def sommario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione sommario chiamata.")
    try:
        category = context.args[0].lower() if context.args else 'generale'
        print(f"Categoria richiesta: {category}")
        news_list = await news_fetcher.get_news(category)  # Aggiunto await

        if news_list:
            print(f"Numero di notizie trovate: {len(news_list)}")
            LAST_NEWS[update.effective_chat.id] = news_list
            summary = "\n".join([f"{i + 1}. {title} ({source})" for i, (title, _, source) in enumerate(news_list)])
            await update.message.reply_text(
                f"Ecco il sommario delle ultime notizie:\n\n{summary}\n\nPer dettagli: /dettaglio N (es: /dettaglio 2)"
            )
        else:
            print("Nessuna notizia trovata.")
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in sommario: {e}")
        await update.message.reply_text("Si è verificato un errore nel generare il sommario.")

async def dettaglio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione dettaglio chiamata.")
    try:
        idx = int(context.args[0]) - 1
        print(f"Indice richiesto: {idx}")
        news_list = LAST_NEWS.get(update.effective_chat.id)
        if news_list and 0 <= idx < len(news_list):
            title, link, source = news_list[idx]
            print(f"Dettaglio notizia: {title}, {source}, {link}")
            msg = f"*{title}* ({source})\n[Leggi qui]({link})"
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            print("Indice non valido o nessuna notizia salvata.")
            await update.message.reply_text("Indice non valido. Usa prima /sommario.")
    except Exception as e:
        print(f"Errore nella funzione dettaglio: {e}")
        await update.message.reply_text("Devi specificare il numero della notizia. Esempio: /dettaglio 2")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistiche del bot (solo admin)"""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("Non autorizzato")
        return

    stats = db.get_stats()
    message = (
        f"👥 Utenti totali: {stats['total_users']}\n"
        f"📰 Notizie inviate: {stats['total_news_sent']}\n"
        f"🕒 Ultimo aggiornamento: {stats['last_update']}"
    )
    await update.message.reply_text(message)

async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie su criptovalute"""
    news_list = await news_fetcher.get_news('cripto')
    if news_list:
        msg = format_news(news_list)
        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text("Nessuna notizia trovata su criptovalute.")

async def ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie su intelligenza artificiale"""
    news_list = await news_fetcher.get_news('ia')
    if news_list:
        msg = format_news(news_list)
        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text("Nessuna notizia trovata su IA.")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cerca notizie per parole chiave"""
    print("Funzione search chiamata.")

    if not context.args:
        await update.message.reply_text("Usa: /cerca <termine di ricerca>")
        return

    try:
        search_term = ' '.join(context.args)
        print(f"Termine di ricerca: {search_term}")

        news_list = await news_fetcher.search_news(search_term)

        if news_list:
            print(f"Risultati trovati: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(
                f"Risultati per '{search_term}':\n\n{msg}",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(f"Nessun risultato trovato per '{search_term}'")

    except Exception as e:
        print(f"Errore nella ricerca: {e}")
        await update.message.reply_text("Si è verificato un errore nella ricerca.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Invia un messaggio a tutti gli utenti (solo admin)"""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("Non autorizzato")
        return

    if not context.args:
        await update.message.reply_text("Usa: /broadcast <messaggio>")
        return

    message = ' '.join(context.args)
    users = db.get_all_users()

    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 Annuncio:\n\n{message}"
            )
        except Exception as e:
            logger.error(f"Errore broadcast a {user['user_id']}: {e}")

    await update.message.reply_text(f"Messaggio inviato a {len(users)} utenti")


async def subscribe_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iscrive il gruppo alle notizie automatiche"""
    try:
        chat_id = update.effective_chat.id
        command_logger.info(f"Ricevuto comando subscribe_group da {chat_id}")

        if update.effective_chat.type == 'private':
            await update.message.reply_text("⚠️ Questo comando funziona solo nei gruppi!")
            return

        db = Database()
        categories = ['generale', 'tech', 'ps5', 'xbox', 'switch', 'pc']
        success = []

        for category in categories:
            try:
                if db.add_subscriber(chat_id=chat_id, category=category, frequency='normal'):
                    success.append(category)
            except Exception as e:
                command_logger.error(f"Errore iscrizione categoria {category}: {e}", exc_info=True)

        if success:
            response = (f"✅ Gruppo iscritto correttamente alle categorie:\n"
                        f"{', '.join(success)}\n\n"
                        f"Ora riceverai gli aggiornamenti automatici!")
            command_logger.info(f"Gruppo {chat_id} iscritto a {len(success)} categorie")
        else:
            response = "❌ Errore durante l'iscrizione del gruppo."
            command_logger.error("Fallita iscrizione gruppo")

        await update.message.reply_text(response)

    except Exception as e:
        command_logger.critical(f"Errore grave in subscribe_group: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ Si è verificato un errore interno.")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra i comandi disponibili"""
    help_text = """
📚 *Guida ai comandi disponibili*:

*/start* - Avvia il bot
*/help* - Mostra questo messaggio
*/news [categoria]* - Notizie dalla categoria specificata
*/sommario [categoria]* - Mostra un sommario delle notizie
*/dettaglio N* - Mostra il dettaglio della notizia N
*/cerca <termine>* - Cerca notizie per parole chiave
*/preferenze* - Imposta le tue preferenze

🎮 *Categorie videogiochi*:
/ps5 - Notizie PlayStation 5
/xbox - Notizie Xbox
/switch - Notizie Nintendo Switch
/pc - Notizie PC Gaming

💻 *Altre categorie*:
/tech - Notizie tecnologia
/ia - Notizie intelligenza artificiale
/crypto - Notizie criptovalute

📌 *Altri comandi*:
/news5 - Ultime 5 notizie
/news10 - Ultime 10 notizie
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione error_handler chiamata.")
    print(f"Errore: {context.error}")