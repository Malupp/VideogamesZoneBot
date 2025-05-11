from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from handlers.auto_send import send_digest
from utils.helpers import format_news
from utils.news_fetcher import news_fetcher
import config as c
from utils.logger import logger
from database.db import Database
from datetime import datetime, timedelta
import logging
import json
from telegram.helpers import escape_markdown

command_logger = logger.getChild('commands')
db = Database()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il comando /start"""
    try:
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)

        welcome_msg = (
            "👋 Ciao! Sono un bot che ti tiene aggiornato sulle ultime notizie di videogiochi e tecnologia.\n\n"
            "Ecco cosa puoi fare:\n"
            "- Usa /news per le ultime notizie\n"
            "- Usa /preferenze per impostare le tue preferenze\n"
            "- Usa /help per vedere tutti i comandi disponibili"
        )

        await update.message.reply_text(welcome_msg)
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("Si è verificato un errore. Riprova più tardi.")


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

🔥 *Comandi Speciali*:
/releases - Ultime uscite e prossimi giochi
/deals - Offerte e sconti giochi
/top - Top notizie del giorno
/filter - Filtra notizie per piattaforma
/digest - Riepilogo giornaliero
/news5 - Ultime 5 notizie
/news10 - Ultime 10 notizie

⚙️ *Comandi Gruppo*:
/group_start - Registra questo gruppo
/group_settings - Impostazioni gruppo
/subscribegroup - Iscrive il gruppo a tutte le categorie
/getchatid - Ottieni l'ID della chat
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra un menu per scegliere lingua, categoria e numero di notizie"""
    try:
        keyboard = [
            [InlineKeyboardButton("\ud83c\uddee\ud83c\uddf9 Italiano", callback_data='news_lang_it'),
             InlineKeyboardButton("\ud83c\uddec\ud83c\udde7 English", callback_data='news_lang_en'),
             InlineKeyboardButton("\ud83c\udf0d Tutte", callback_data='news_lang_all')],
            [InlineKeyboardButton("\ud83c\udfae Generale", callback_data='news_cat_generale'),
             InlineKeyboardButton("\ud83d\udd79\ufe0f PS5", callback_data='news_cat_ps5'),
             InlineKeyboardButton("\ud83d\udfe9 Xbox", callback_data='news_cat_xbox')],
            [InlineKeyboardButton("\ud83d\udfe5 Switch", callback_data='news_cat_switch'),
             InlineKeyboardButton("\ud83d\udcbb PC", callback_data='news_cat_pc'),
             InlineKeyboardButton("\ud83d\udcf1 Tech", callback_data='news_cat_tech')],
            [InlineKeyboardButton("\ud83e\udde0 IA", callback_data='news_cat_ia'),
             InlineKeyboardButton("\u20bf Crypto", callback_data='news_cat_cripto')],
            [InlineKeyboardButton("5 Notizie", callback_data='news_limit_5'),
             InlineKeyboardButton("10 Notizie", callback_data='news_limit_10'),
             InlineKeyboardButton("20 Notizie", callback_data='news_limit_20')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            '📰 *Scegli lingua, categoria e numero di notizie da visualizzare*:',
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in news command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


# State for user news preferences (in-memory, for demo)
USER_NEWS_PREFS = {}


async def handle_news_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la selezione di lingua/categoria/limite per le news"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data

    # Get or set default user prefs
    prefs = USER_NEWS_PREFS.get(user_id, {'lang': 'all', 'cat': 'generale', 'limit': 5})

    if data.startswith('news_lang_'):
        lang = data.split('_')[-1]
        prefs['lang'] = lang
    elif data.startswith('news_cat_'):
        cat = data.split('_')[-1]
        prefs['cat'] = cat
    elif data.startswith('news_limit_'):
        limit = int(data.split('_')[-1])
        prefs['limit'] = limit

    USER_NEWS_PREFS[user_id] = prefs

    # Compose category for fetcher
    if prefs['cat'] == 'generale':
        if prefs['lang'] == 'it':
            category = 'generale_it'
        elif prefs['lang'] == 'en':
            category = 'generale_en'
        else:
            category = 'generale'
    else:
        category = prefs['cat']

    # Fetch news
    try:
        news_list = await news_fetcher.get_news(category, limit=prefs['limit'])
        if news_list:
            msg = "\n\n".join([
                f"*{i+1}\\. {escape_markdown(title, version=2)}*\n"
                f"[{escape_markdown(source, version=2)}]({escape_markdown(link, version=2)}) \\| "
                f"{escape_markdown(date, version=2)} \\| {escape_markdown(lang.upper(), version=2)}"
                for i, (title, link, source, date, lang) in enumerate(news_list)
            ])
            await query.edit_message_text(msg, parse_mode="MarkdownV2", disable_web_page_preview=True)
        else:
            await query.edit_message_text("Nessuna notizia trovata per questa selezione.")
    except Exception as e:
        logger.error(f"Error in handle_news_buttons: {e}")
        await query.edit_message_text("Errore nel recupero delle notizie o nella formattazione del messaggio.")


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

    if choice == 'pref_games':
        # Rimuovi tutte le categorie tranne quelle di gaming
        current_categories = db.get_user_categories(user_id)
        for cat in current_categories:
            if cat not in ['ps5', 'xbox', 'switch', 'pc']:
                db.unsubscribe(user_id, cat)

        # Iscrivi alle categorie gaming se non già iscritto
        for cat in ['ps5', 'xbox', 'switch', 'pc']:
            if cat not in current_categories:
                db.add_subscriber(user_id, cat, 'normal')

        response = "Preferenza impostata: solo videogiochi 🎮"
    elif choice == 'pref_tech':
        # Rimuovi tutte le categorie tranne tech
        current_categories = db.get_user_categories(user_id)
        for cat in current_categories:
            if cat not in ['tech', 'ia', 'crypto']:
                db.unsubscribe(user_id, cat)

        # Iscrivi alle categorie tech se non già iscritto
        for cat in ['tech', 'ia', 'crypto']:
            if cat not in current_categories:
                db.add_subscriber(user_id, cat, 'normal')

        response = "Preferenza impostata: solo tech 💻"
    else:  # pref_both
        # Iscrivi a tutte le categorie principali
        for cat in ['generale', 'tech', 'ps5', 'xbox', 'switch', 'pc']:
            db.add_subscriber(user_id, cat, 'normal')

        response = "Preferenza impostata: videogiochi e tech 🎮+💻"

    await query.edit_message_text(text=response)
    db.update_user_activity(user_id)


async def handle_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la frequenza di invio"""
    query = update.callback_query
    await query.answer()

    choice = query.data
    user_id = query.from_user.id

    # Ottieni le preferenze attuali
    prefs = db.get_user_preferences(user_id) or {}

    if choice == 'freq_high':
        prefs['frequency'] = 'high'
        response = "Frequenza impostata: aggiornamenti frequenti 🔔"
    else:
        prefs['frequency'] = 'low'
        response = "Frequenza impostata: aggiornamenti ridotti 🔕"

    # Salva le preferenze
    with db._get_connection() as conn:
        conn.execute(
            "UPDATE users SET preferences = ? WHERE user_id = ?",
            (json.dumps(prefs), user_id)
        )

    await query.edit_message_text(text=response)
    db.update_user_activity(user_id)


async def ps5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie PS5"""
    try:
        news_list = await news_fetcher.get_news('ps5')
        if news_list:
            msg = f"🎮 *Ultime notizie PS5*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per PS5.")
    except Exception as e:
        logger.error(f"Error in ps5 command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def xbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie Xbox"""
    try:
        news_list = await news_fetcher.get_news('xbox')
        if news_list:
            msg = f"🎮 *Ultime notizie Xbox*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per Xbox.")
    except Exception as e:
        logger.error(f"Error in xbox command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie Nintendo Switch"""
    try:
        news_list = await news_fetcher.get_news('switch')
        if news_list:
            msg = f"🎮 *Ultime notizie Nintendo Switch*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per Nintendo Switch.")
    except Exception as e:
        logger.error(f"Error in switch command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie PC Gaming"""
    try:
        news_list = await news_fetcher.get_news('pc')
        if news_list:
            msg = f"💻 *Ultime notizie PC Gaming*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per PC Gaming.")
    except Exception as e:
        logger.error(f"Error in pc command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def tech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie tecnologia"""
    try:
        news_list = await news_fetcher.get_news('tech')
        if news_list:
            msg = f"💻 *Ultime notizie Tecnologia*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per Tecnologia.")
    except Exception as e:
        logger.error(f"Error in tech command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie criptovalute"""
    try:
        news_list = await news_fetcher.get_news('cripto')
        if news_list:
            msg = f"💰 *Ultime notizie Criptovalute*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per Criptovalute.")
    except Exception as e:
        logger.error(f"Error in crypto command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notizie intelligenza artificiale"""
    try:
        news_list = await news_fetcher.get_news('ia')
        if news_list:
            msg = f"🤖 *Ultime notizie Intelligenza Artificiale*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per IA.")
    except Exception as e:
        logger.error(f"Error in ai command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def news_5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ultime 5 notizie"""
    try:
        news_list = await news_fetcher.get_news('generale', limit=5)
        if news_list:
            msg = f"📰 *Ultime 5 notizie*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        logger.error(f"Error in news_5 command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")


async def news_10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra le ultime 10 notizie"""
    try:
        news_list = await news_fetcher.get_news('generale', limit=10)
        if news_list:
            msg = "\n\n".join([
                f"*{i+1}\\. {escape_markdown(title, version=2)}*\n"
                f"[{escape_markdown(source, version=2)}]({escape_markdown(link, version=2)}) \\| "
                f"{escape_markdown(date, version=2)} \\| {escape_markdown(lang.upper(), version=2)}"
                for i, (title, link, source, date, lang) in enumerate(news_list)
            ])
            await update.message.reply_text(msg, parse_mode="MarkdownV2", disable_web_page_preview=True)
        else:
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        logger.error(f"Error in news_10 command: {e}")
        await update.message.reply_text("Errore nel recupero delle notizie.")


LAST_NEWS = {}


async def sommario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra un sommario delle notizie"""
    try:
        category = context.args[0].lower() if context.args else 'generale'
        logger.info(f"Fetching summary for category: {category}")

        news_list = await news_fetcher.get_news(category)

        if news_list:
            LAST_NEWS[update.effective_chat.id] = news_list
            summary = "\n".join([f"{i + 1}. {title} ({source})" for i, (title, _, source) in enumerate(news_list)])
            await update.message.reply_text(
                f"📰 *Sommario notizie {category.upper()}*\n\n{summary}\n\n"
                "Per dettagli: /dettaglio N (es: /dettaglio 2)",
                parse_mode="Markdown"
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per questa categoria.")
    except Exception as e:
        logger.error(f"Error in sommario command: {e}")
        await update.message.reply_text("Si è verificato un errore nel generare il sommario.")


async def dettaglio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra il dettaglio di una notizia"""
    try:
        if not context.args:
            raise ValueError("Numero mancante")

        idx = int(context.args[0]) - 1
        news_list = LAST_NEWS.get(update.effective_chat.id)

        if news_list and 0 <= idx < len(news_list):
            title, link, source = news_list[idx]
            msg = f"📰 *Dettaglio notizia*\n\n*{title}* ({source})\n[Leggi qui]({link})"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Indice non valido. Usa prima /sommario.")
    except ValueError:
        await update.message.reply_text("Devi specificare il numero della notizia. Esempio: /dettaglio 2")
    except Exception as e:
        logger.error(f"Error in dettaglio command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero del dettaglio.")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cerca notizie per parole chiave"""
    if not context.args:
        await update.message.reply_text("Usa: /cerca <termine di ricerca>")
        return

    try:
        search_term = ' '.join(context.args)
        logger.info(f"Searching for: {search_term}")

        news_list = await news_fetcher.search_news(search_term)

        if news_list:
            msg = f"🔍 *Risultati per '{search_term}'*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text(f"Nessun risultato trovato per '{search_term}'")
    except Exception as e:
        logger.error(f"Error in search command: {e}")
        await update.message.reply_text("Si è verificato un errore nella ricerca.")

async def subscribe_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Versione semplificata e completamente robusta"""
    try:
        chat_id = update.effective_chat.id
        command_logger.info(f"Processing /subscribegroup for {chat_id}")

        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Comando valido solo per gruppi!")
            return

        categories = ['generale', 'tech', 'ps5', 'xbox', 'switch', 'pc']
        success = []

        for category in categories:
            try:
                if db.add_subscriber(chat_id=chat_id, category=category, frequency='normal'):
                    success.append(category)
            except Exception as e:
                command_logger.warning(f"Category {category} error: {str(e)}")
                continue

        if success:
            response = (
                f"✅ Gruppo iscritto correttamente a {len(success)} categorie!\n\n"
                f"• {', '.join(success)}\n\n"
                f"Gli aggiornamenti inizieranno con il prossimo invio automatico."
            )
            command_logger.info(f"Gruppo {chat_id} registrato per {len(success)} categorie")
        else:
            response = "⚠️ Il gruppo era già iscritto a tutte le categorie"
            command_logger.info(f"Gruppo {chat_id} già registrato")

        await update.message.reply_text(response)

    except Exception as e:
        command_logger.critical(f"Fatal error in subscribe_group: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Si è verificato un errore. Riprova più tardi.")


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restituisce l'ID della chat"""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"L'ID di questa chat è: `{chat_id}`", parse_mode="Markdown")
    db.update_user_activity(update.effective_user.id)


async def group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce l'aggiunta del bot a un gruppo"""
    chat = update.effective_chat
    if chat.type == 'private':
        await update.message.reply_text("Questo comando funziona solo nei gruppi!")
        return

    try:
        if db.add_group(chat.id, chat.title):
            response = (
                "✅ *Gruppo registrato con successo!*\n\n"
                "Ora puoi configurare le categorie di notizie che vuoi ricevere.\n"
                "Usa /group_settings per modificare le preferenze"
            )
        else:
            response = "ℹ️ Il gruppo è già registrato. Usa /group_settings per modificare le preferenze"

        await update.message.reply_text(response, parse_mode="Markdown")
        db.update_user_activity(update.effective_user.id)
    except Exception as e:
        logger.error(f"Error in group_start: {e}")
        await update.message.reply_text("❌ Si è verificato un errore durante la registrazione")


async def group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu impostazioni gruppo"""
    chat = update.effective_chat
    if chat.type == 'private':
        await update.message.reply_text("Questo comando funziona solo nei gruppi!")
        return

    try:
        categories = db.get_user_categories(chat.id)
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if 'generale' in categories else '❌'} Generale",
                callback_data=f"group_toggle:generale:{chat.id}")],
            [InlineKeyboardButton(
                f"{'✅' if 'tech' in categories else '❌'} Tech",
                callback_data=f"group_toggle:tech:{chat.id}")],
            [InlineKeyboardButton(
                f"{'✅' if 'ps5' in categories else '❌'} PS5",
                callback_data=f"group_toggle:ps5:{chat.id}")],
            [InlineKeyboardButton(
                f"{'✅' if 'xbox' in categories else '❌'} Xbox",
                callback_data=f"group_toggle:xbox:{chat.id}")],
            [InlineKeyboardButton(
                f"{'✅' if 'switch' in categories else '❌'} Switch",
                callback_data=f"group_toggle:switch:{chat.id}")],
            [InlineKeyboardButton(
                f"{'✅' if 'pc' in categories else '❌'} PC",
                callback_data=f"group_toggle:pc:{chat.id}")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚙️ *Impostazioni Gruppo*\n\nSeleziona le categorie di notizie da ricevere:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        db.update_user_activity(update.effective_user.id)
    except Exception as e:
        logger.error(f"Error in group_settings: {e}")
        await update.message.reply_text("❌ Errore nel caricamento delle impostazioni")


async def group_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la selezione delle categorie"""
    query = update.callback_query
    await query.answer()

    try:
        _, category, group_id = query.data.split(':')
        group_id = int(group_id)

        current_categories = db.get_user_categories(group_id)
        if category in current_categories:
            db.unsubscribe(group_id, category)
            new_status = "❌"
        else:
            db.add_subscriber(group_id, category, 'normal')
            new_status = "✅"

        # Aggiorna il messaggio
        keyboard = []
        all_categories = ['generale', 'tech', 'ps5', 'xbox', 'switch', 'pc']
        current_categories = db.get_user_categories(group_id)

        for cat in all_categories:
            keyboard.append([
                InlineKeyboardButton(
                    f"{'✅' if cat in current_categories else '❌'} {cat.capitalize()}",
                    callback_data=f"group_toggle:{cat}:{group_id}")
            ])

        await query.edit_message_text(
            text="⚙️ *Impostazioni Gruppo*\n\nSeleziona le categorie di notizie da ricevere:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in group_toggle_callback: {e}")
        await query.edit_message_text("❌ Si è verificato un errore")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra le statistiche del bot (solo admin)"""
    try:
        user_id = update.effective_user.id
        if user_id not in c.Config.ADMIN_IDS:
            await update.message.reply_text("❌ Accesso negato")
            return

        # Ottieni statistiche dal database
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Totale utenti
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']

            # Totale notizie inviate
            cursor.execute("SELECT SUM(news_received) as total FROM user_stats")
            total_news_sent = cursor.fetchone()['total'] or 0

            # Gruppi attivi
            cursor.execute("SELECT COUNT(*) as count FROM groups WHERE is_active = 1")
            active_groups = cursor.fetchone()['count']

        message = (
            "📊 *Statistiche Bot*\n\n"
            f"• Utenti totali: {total_users}\n"
            f"• Notizie inviate: {total_news_sent}\n"
            f"• Gruppi attivi: {active_groups}\n\n"
            f"Ultimo aggiornamento: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        await update.message.reply_text(message, parse_mode="Markdown")
        db.update_user_activity(user_id)
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text("❌ Errore nel recupero delle statistiche")


async def debug_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lo stato dello scheduler"""
    try:
        # Verifica che lo scheduler esista
        if not hasattr(context.application, 'scheduler') or context.application.scheduler is None:
            await update.message.reply_text("⚠️ Scheduler non inizializzato")
            return

        # Verifica permessi (admin bot o admin gruppo)
        is_bot_admin = update.effective_user.id in c.Config.ADMIN_IDS
        is_group_admin = False
        
        if update.effective_chat.type in ['group', 'supergroup']:
            member = await context.bot.get_chat_member(
                update.effective_chat.id,
                update.effective_user.id
            )
            is_group_admin = member.status in ['creator', 'administrator']
        
        if not (is_bot_admin or is_group_admin):
            await update.message.reply_text("❌ Questo comando è riservato agli amministratori")
            return

        # Accedi allo scheduler direttamente dall'applicazione bot
        bot_app = context.application
        if not hasattr(bot_app, 'scheduler') or not bot_app.scheduler:
            await update.message.reply_text("⚠️ Scheduler non inizializzato")
            return

        jobs = bot_app.scheduler.get_jobs()
        if not jobs:
            await update.message.reply_text("⚠️ Nessun job attivo nello scheduler")
            return

        message = "📊 *Stato Scheduler*:\n\n"
        for job in jobs:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            interval = str(job.trigger.interval) if hasattr(job.trigger, 'interval') else "Una tantum"

            message += (
                f"• *{job.id}*\n"
                f"  ⏱️ Prossima esecuzione: `{next_run}`\n"
                f"  🔄 Intervallo: `{interval}`\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Errore in debug_scheduler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ Errore nel recupero dello scheduler\n"
            f"Errore: {str(e)}"
        )


async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test invio notizie (solo admin)"""
    try:
        user_id = update.effective_user.id
        if user_id not in c.Config.ADMIN_IDS:
            await update.message.reply_text("❌ Accesso negato")
            return

        await update.message.reply_text("⚙️ **Test avviato**: provo a inviare notizie...")

        # Forza l'invio immediato per la categoria 'generale'
        from handlers.auto_send import send_news_to_subscribers
        result = await send_news_to_subscribers(
            context.bot,
            'generale',
            force_update=True
        )

        await update.message.reply_text(
            f"✅ **Test completato!**\n"
            f"Notizie inviate a *{result}* utenti/gruppi.",
            parse_mode="Markdown"
        )
        db.update_user_activity(user_id)
    except Exception as e:
        logger.error(f"Error in test_send: {e}")
        await update.message.reply_text("❌ Errore durante il test. Controlla i log.")


async def debug_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando per debuggare il database degli iscritti"""
    try:
        # Verifica permessi admin
        if update.effective_user.id not in c.Config.ADMIN_IDS:
            await update.message.reply_text("Comando riservato agli amministratori")
            return

        # Controlla il database
        await update.message.reply_text("🔍 Analisi database in corso...")

        # Ottieni statistiche
        user_count = db.get_user_count()
        subscriber_stats = {}
        for category in ['generale', 'tech', 'ps5', 'xbox', 'pc', 'switch', 'ia', 'cripto']:
            subscribers = db.get_subscribers(category)
            subscriber_stats[category] = len(subscribers)

        stats_text = "📊 *Statistiche Database*\n\n"
        stats_text += f"Utenti totali: {user_count}\n\n"
        stats_text += "*Iscritti per categoria:*\n"
        for cat, count in subscriber_stats.items():
            stats_text += f"- {cat.capitalize()}: {count}\n"

        await update.message.reply_text(stats_text, parse_mode="Markdown")

        # Se non ci sono iscritti alla categoria generale, aggiungi chi invia il comando
        if subscriber_stats['generale'] == 0:
            user_id = update.effective_user.id
            db.subscribe(user_id, 'generale')
            await update.message.reply_text(
                "✅ *Database riparato*\nTi ho aggiunto come utente test per la categoria 'generale'.",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Errore in debug_database: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Errore: {str(e)}")

async def releases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra le ultime uscite e i prossimi giochi"""
    try:
        news_list = await news_fetcher.search_news("release data uscita lancio nuovo gioco", limit=5)
        if news_list:
            msg = f"🎲 *Ultime Uscite e Prossimi Giochi*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata sulle uscite.")
    except Exception as e:
        logger.error(f"Error in releases command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle uscite.")

async def deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra le offerte e sconti dei giochi"""
    try:
        news_list = await news_fetcher.search_news("offerta sconto prezzo ribasso giochi", limit=5)
        if news_list:
            msg = f"💰 *Offerte e Sconti Giochi*\n\n{format_news(news_list)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna offerta trovata al momento.")
    except Exception as e:
        logger.error(f"Error in deals command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle offerte.")

async def top_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra le notizie più importanti del giorno"""
    try:
        # Recupera notizie da tutte le categorie
        all_news = []
        categories = ['generale', 'tech', 'ps5', 'xbox', 'switch', 'pc']
        
        for category in categories:
            news = await news_fetcher.get_news(category, limit=1)
            if news:
                all_news.extend(news)
        
        # Prendi le top 5 notizie
        top_5 = all_news[:5]
        
        if top_5:
            msg = f"🏆 *TOP NEWS DEL GIORNO*\n\n{format_news(top_5)}"
            await update.message.reply_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            db.update_user_activity(update.effective_user.id)
        else:
            await update.message.reply_text("Nessuna notizia trovata per oggi.")
    except Exception as e:
        logger.error(f"Error in top_news command: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle top news.")

async def filter_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtra notizie per piattaforma con bottoni inline"""
    keyboard = [
        [
            InlineKeyboardButton("🎮 PS5", callback_data='filter_ps5'),
            InlineKeyboardButton("🟩 Xbox", callback_data='filter_xbox'),
            InlineKeyboardButton("🔴 Switch", callback_data='filter_switch')
        ],
        [
            InlineKeyboardButton("💻 PC", callback_data='filter_pc'),
            InlineKeyboardButton("📱 Tech", callback_data='filter_tech'),
            InlineKeyboardButton("🎯 Tutte", callback_data='filter_all')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🔍 *Filtra Notizie per Piattaforma*\n'
        'Seleziona la piattaforma per vedere le ultime notizie:',
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la selezione del filtro notizie"""
    query = update.callback_query
    await query.answer()
    
    platform = query.data.replace('filter_', '')
    if platform == 'all':
        news_list = await news_fetcher.get_news('generale', limit=5)
    else:
        news_list = await news_fetcher.get_news(platform, limit=5)
    
    if news_list:
        msg = f"📰 *Ultime notizie {platform.upper()}*\n\n{format_news(news_list)}"
        await query.edit_message_text(
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await query.edit_message_text(f"Nessuna notizia trovata per {platform}.")

async def daily_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Invia un riepilogo delle notizie più importanti del giorno"""
    try:
        user_id = update.effective_user.id
        await send_digest(context.bot, user_id)
        db.update_user_activity(user_id)
    except Exception as e:
        logger.error(f"Error in daily_digest command: {e}")
        await update.message.reply_text("Si è verificato un errore nell'invio del digest giornaliero.")


async def lingua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permette di scegliere la lingua preferita per le news"""
    keyboard = [
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data='set_lang_it'),
         InlineKeyboardButton("🇬🇧 English", callback_data='set_lang_en'),
         InlineKeyboardButton("🌍 Tutte", callback_data='set_lang_all')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '🌐 *Scegli la lingua preferita per le notizie*:',
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    lang = data.split('_')[-1]
    # Save to user prefs (in-memory for demo)
    prefs = USER_NEWS_PREFS.get(user_id, {'lang': 'all', 'cat': 'generale', 'limit': 5})
    prefs['lang'] = lang
    USER_NEWS_PREFS[user_id] = prefs
    await query.edit_message_text(f"Lingua preferita impostata su: {lang.upper()}")

async def becomeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permette di aggiungere il proprio user ID agli admin del bot (solo in chat privata)"""
    user = update.effective_user
    chat = update.effective_chat
    if chat.type != 'private':
        await update.message.reply_text("❌ Questo comando può essere usato solo in chat privata per motivi di sicurezza.")
        return
    if user.id in c.Config.ADMIN_IDS:
        await update.message.reply_text(f"✅ Sei già admin del bot! Il tuo user ID è: `{user.id}`", parse_mode="Markdown")
        return
    c.Config.ADMIN_IDS.append(user.id)
    await update.message.reply_text(f"✅ Ora sei admin del bot! Il tuo user ID è: `{user.id}`\n\n*Nota:* questa modifica è temporanea e verrà persa al riavvio del bot. Per renderla permanente, aggiungi manualmente il tuo user ID in .env o config.py.", parse_mode="Markdown")
