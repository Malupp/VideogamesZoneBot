# utils/helpers.py
def format_news(news_list: list, include_source: bool = True) -> str:
    """Formatta una lista di notizie per l'invio"""
    formatted = []
    for idx, (title, url, source) in enumerate(news_list, 1):
        source_text = f" ({source})" if include_source else ""
        formatted.append(f"{idx}. *{title}*{source_text}\n[Leggi qui]({url})")
    return "\n\n".join(formatted)