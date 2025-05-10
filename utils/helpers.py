# utils/helpers.py
def format_news(news_list: list, include_source: bool = True) -> str:
    """Formatta una lista di notizie per l'invio con emoji e migliore leggibilità"""
    formatted = []
    
    # Emoji per diverse categorie di notizie
    category_emojis = {
        'PS5': '🎮',
        'Xbox': '🟩',
        'Switch': '🔴',
        'PC': '💻',
        'Tech': '📱',
        'IA': '🤖',
        'Crypto': '💰',
        'Generale': '🎯'
    }

    for idx, (title, url, source) in enumerate(news_list, 1):
        # Determina l'emoji appropriata basata sulla fonte o usa l'emoji default
        emoji = '📢'
        for category, cat_emoji in category_emojis.items():
            if category.lower() in source.lower():
                emoji = cat_emoji
                break

        # Formatta la notizia con stile migliorato
        source_text = f"_{source}_" if include_source else ""
        formatted.append(
            f"{emoji} *{idx}. {title}*\n"
            f"{source_text}\n"
            f"➡️ [Leggi l'articolo completo]({url})"
        )
    
    return "\n\n" + "\n\n".join(formatted) + "\n\n💡 _Usa /dettaglio [numero] per maggiori informazioni_"