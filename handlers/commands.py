from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from utils.helpers import format_news
from utils.news_fetcher import get_news, news_fetcher
import config
from utils.logger import logger
from database.db import Database
from datetime import datetime, timedelta
from handlers.auto_send import test_send, send_news_to_subscribers
import logging

command_logger = logger.getChild('commands')
db = Database()

# Funzione di benvenuto
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione start chiamata.")
    print("Comando /start ricevuto.")
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

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione news chiamata.")
    try:
        category = context.args[0].lower() if context.args else 'generale'
        print(f"Categoria richiesta: {category}")
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

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione get_chat_id chiamata.")
    chat_id = update.message.chat.id
    print(f"chat_id del gruppo: {chat_id}")
    await update.message.reply_text(f"Il chat_id di questo gruppo è: {chat_id}")

async def ps5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione ps5 chiamata.")
    try:
        news_list = await news_fetcher.get_news('ps5')
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
        news_list = await news_fetcher.get_news('xbox')
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
        news_list = await news_fetcher.get_news('switch')
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
        news_list = await news_fetcher.get_news('pc')
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
        news_list = await news_fetcher.get_news('tech')
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
        news_list = await get_news(limit=5)
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
        news_list = await get_news(limit=10)
        if news_list:
            print(f"Numero di notizie trovate: {len(news_list)}")
            msg = format_news(news_list)
            await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await update.message.reply_text("Nessuna notizia trovata.")
    except Exception as e:
        print(f"Errore in news_10: {e}")
        await update.message.reply_text("Si è verificato un errore nel recupero delle notizie.")

LAST_NEWS = {}

async def sommario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Funzione sommario chiamata.")
    try:
        category = context.args[0].lower() if context.args else 'generale'
        print(f"Categoria richiesta: {category}")
        news_list = await news_fetcher.get_news(category)

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
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ Accesso negato")
            return

        total_users = db.get_total_users()
        total_news_sent = db.get_total_news_sent()
        active_groups = db.get_active_groups()

        message = (
            "📊 *Statistiche Bot*\n\n"
            f"• Utenti totali: {total_users}\n"
            f"• Notizie inviate: {total_news_sent}\n"
            f"• Gruppi attivi: {len(active_groups)}\n\n"
            f"Ultimo aggiornamento: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text("❌ Errore nel recupero delle statistiche")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistiche del bot (solo admin)"""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("Non autorizzato")
        return

    total_users = db.get_total_users()
    total_news_sent = db.get_total_news_sent()

    message = (
        f"👥 Utenti totali: {total_users}\n"
        f"📰 Notizie inviate: {total_news_sent}\n"
        f"🕒 Ultimo aggiornamento: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
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


async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando di test per verificare l'invio automatico"""
    try:
        await update.message.reply_text("⚙️ **Test avviato**: provo a inviare notizie...")

        # Forza l'invio immediato per la categoria 'generale'
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
    except Exception as e:
        logger.error(f"Errore durante test_send: {e}", exc_info=True)
        await update.message.reply_text("❌ Errore durante il test. Controlla i log.")

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


async def debug_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lo stato dello scheduler"""
    jobs = context.application.scheduler.get_jobs()
    if not jobs:
        await update.message.reply_text("⚠️ Nessun job attivo nello scheduler")
        return

    message = "📊 Stato Scheduler:\n\n"
    for job in jobs:
        message += (
            f"• {job.id}\n"
            f"  Prossima esecuzione: {job.next_run_time}\n"
            f"  Intervallo: {job.trigger.interval}\n\n"
        )

    await update.message.reply_text(message)