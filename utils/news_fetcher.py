import feedparser
from urllib.parse import urlparse
from typing import List, Tuple, Dict, Optional
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
import ssl

# Configurazione logging
logger = logging.getLogger(__name__)


class NewsFetcher:
    def __init__(self):
        self.RSS_FEEDS = {
            'generale': [
                'https://it.ign.com/feed.xml',
                'https://www.everyeye.it/rss/news.xml',
                'https://www.gamesource.it/feed/gn',
                'https://www.gametimers.it/feed/',
                'https://www.spaziogames.it/rss',
                'https://multiplayer.it/feed/',
                'https://www.eurogamer.net/feed',
                'https://www.eurogamer.net/feed/features'
                'https://kotaku.com/rss',
                'https://www.gameinformer.com/news.xml',
                'https://www.rockpapershotgun.com/feed/features',
                'https://www.timeextension.com/feeds/articles/tags/Features',
                'https://www.thegamer.com/feed/category/tg-originals/',
                'https://www.techradar.com/uk/feeds/articletype/feature',
                'https://press-start.xyz/feed/',
                'https://www.gamespot.com/feeds/mashup/',
                'https://feeds.feedburner.com/ign/all',
                'https://feeds.feedburner.com/ign/games-all',
                'https://feeds.hwupgrade.it/rss_hwup.xml',
                'https://www.gamesindustry.biz/feed',
                'https://www.vg247.com/feed',
                'https://www.gamespot.com/feeds/mashup',
                'https://www.polygon.com/rss/index.xml',
                'https://www.gematsu.com/feed',
                'https://gamingintel.com/feed/'

            ],
            'ps5': [
                'https://www.everyeye.it/rss/playstation.xml',
                'https://it.ign.com/feed/ps5',
                'https://www.mondoxbox.com/feed/',
                'https://blog.playstation.com/feed/'
            ],
            'xbox': [
                'https://www.everyeye.it/rss/xbox.xml',
                'https://it.ign.com/feed/xbox-series-x',
                'https://www.mondoxbox.com/feed/',
                'https://news.xbox.com/en-us/feed/'
            ],
            'pc': [
                'https://www.everyeye.it/rss/pc.xml',
                'https://it.ign.com/feed/pc',
                'https://www.pcgamer.com/rss/',
                'https://www.pcgamesn.com/mainrss.xml'
            ],
            'switch': [
                'https://www.everyeye.it/rss/nintendo.xml',
                'https://it.ign.com/feed/nintendo-switch',
                'https://www.nintendolife.com/feeds/latest'
            ],
            'tech': [
                'https://www.hwupgrade.it/feed/',
                'https://www.tomshw.it/feed/',
                'https://www.polygon.com/rss/features/index.xml',
                'https://feeds.arstechnica.com/arstechnica/features',
                'https://tftcentral.co.uk/category/articles/feed',
                'https://feeds.feedburner.com/techspot/reviews',
                'https://feeds.feedburner.com/ign/tech-articles'
            ],
            'movies': [
                'https://www.everyeye.it/rss/cinema.xml',
                'https://it.ign.com/feed/film',
                'https://www.cinemablend.com/rss/news',
                'https://www.cinematographe.it/feed/',
                'https://www.film.it/rss/',
                'https://www.filmfestivals.com/blogs/feed',
                'https://www.filmfreakcentral.net/ffc/feed/',
                'https://feeds.feedburner.com/ign/movies-articles',
                'https://www.theverge.com/movies/rss/index.xml',
                'https://www.theverge.com/rss/tag/movies/index.xml',
            ],
            'ia': [
                'https://www.ai4business.it/feed/',
                'https://www.intelligenza-artificiale.net/feed/'
            ],
            'cripto': [
                'https://it.cointelegraph.com/rss',
                'https://www.cryptonomist.it/feed/'
            ]
        }

        self.cache = {}
        self.last_fetch = {}
        self.session = None
        self._initialized = False

    async def initialize(self):
        """Initialize aiohttp session"""
        if not self._initialized:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context),
                timeout=aiohttp.ClientTimeout(total=20)
            )
            self._initialized = True
            logger.info("Initialized aiohttp session")
            print("[DEBUG] Initialized aiohttp session")

    async def ensure_initialized(self):
        """Ensure the session is initialized before use"""
        if not self._initialized:
            await self.initialize()

    async def fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """Fetch a single RSS feed with caching"""
        print(f"[DEBUG] Fetching feed: {url}")

        # Ensure session is initialized
        await self.ensure_initialized()

        now = datetime.now()
        # Usa cache se disponibile e recente (meno di 10 minuti)
        if url in self.cache and now - self.last_fetch.get(url, datetime.min) < timedelta(minutes=10):
            print(f"[DEBUG] Using cached version of {url}")
            return self.cache[url]

        try:
            # Timeout e gestione errori migliorata
            async with self.session.get(url, timeout=10, raise_for_status=True) as response:
                text = await response.text()
                feed = feedparser.parse(text)

                # Verifica se il feed è valido
                if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                    logger.warning(f"Feed {url} returned no entries")
                    print(f"[WARNING] Feed {url} returned no entries")
                    return feedparser.FeedParserDict({'entries': []})

                self.cache[url] = feed
                self.last_fetch[url] = now
                print(f"[DEBUG] Successfully fetched {url}, found {len(feed.entries)} entries")
                return feed

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            print(f"[ERROR] HTTP error fetching {url}: {e}")
            return feedparser.FeedParserDict({'entries': []})
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            print(f"[ERROR] Timeout fetching {url}")
            return feedparser.FeedParserDict({'entries': []})
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}", exc_info=True)
            print(f"[ERROR] Failed to fetch {url}: {e}")
            return feedparser.FeedParserDict({'entries': []})

    async def get_news(self, category: str = 'generale', limit: int = 5, keywords: Optional[List[str]] = None) -> List[
        Tuple[str, str, str]]:
        """Get news from multiple sources with optional keyword filtering"""
        print(f"[DEBUG] Getting news for category: {category}, limit: {limit}")

        try:
            # Assicurati che la sessione sia inizializzata
            await self.ensure_initialized()

            urls = self.RSS_FEEDS.get(category.lower(), [])
            if not urls:
                logger.warning(f"No URLs found for category: {category}")
                print(f"[WARNING] No URLs found for category: {category}")

                # Fallback a generale se la categoria non esiste
                if category.lower() != 'generale':
                    print(f"[INFO] Falling back to 'generale' category")
                    urls = self.RSS_FEEDS.get('generale', [])

                # Se ancora non ci sono URL, ritorna lista vuota
                if not urls:
                    return []

            # Fetching parallelo dei feed
            tasks = [self.fetch_feed(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_entries = []
            for i, (result, url) in enumerate(zip(results, urls)):
                # Salta i feed con errori
                if isinstance(result, Exception):
                    logger.error(f"Error processing feed {url}: {result}")
                    print(f"[ERROR] Failed to process feed {url}: {result}")
                    continue

                domain = urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()

                # Gestisci il caso in cui 'entries' non esista
                entries = getattr(result, 'entries', [])
                if not entries:
                    print(f"[WARNING] No entries found in feed {url}")
                    continue

                for entry in entries[:limit * 2]:
                    try:
                        title = getattr(entry, 'title', 'Titolo non disponibile')
                        link = getattr(entry, 'link', '')

                        # Salta se non c'è un link valido
                        if not link:
                            continue

                        # Cerca di estrarre la data di pubblicazione
                        published = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published = entry.published_parsed
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            published = entry.updated_parsed

                        # Verifica filtro keywords se presenti
                        if keywords and not any(kw.lower() in title.lower() for kw in keywords):
                            continue

                        all_entries.append((title, link, domain, published))
                    except Exception as e:
                        logger.error(f"Error processing entry in {url}: {e}")
                        print(f"[ERROR] Error processing entry: {e}")
                        continue

            # Ordina per data se disponibile, altrimenti mantieni l'ordine originale
            all_entries.sort(key=lambda x: x[3] or (0,), reverse=True)

            # Rimuovi duplicati mantenendo l'ordine
            unique_entries = []
            seen = set()
            for entry in all_entries:
                if entry[1] not in seen:  # Usa l'URL come chiave per i duplicati
                    seen.add(entry[1])
                    unique_entries.append(entry[:3])  # Salva solo titolo, link, fonte
                    if len(unique_entries) >= limit:
                        break

            print(f"[DEBUG] Returning {len(unique_entries)} news items")
            return unique_entries

        except Exception as e:
            logger.error(f"Error in get_news for {category}: {e}", exc_info=True)
            print(f"[ERROR] Failed to get news for {category}: {e}")
            return []

    async def search_news(self, search_term: str, limit: int = 5) -> List[Tuple[str, str, str]]:
        """Search news across all categories"""
        print(f"[DEBUG] Searching for: {search_term}")

        if not search_term.strip():
            logger.warning("Empty search term provided")
            return []

        results = []
        keywords = search_term.lower().split()

        # Cerca in tutte le categorie
        tasks = []
        for category in self.RSS_FEEDS.keys():
            tasks.append(self.get_news(category, limit * 2))

        # Esegui tutte le ricerche in parallelo
        category_results = await asyncio.gather(*tasks, return_exceptions=True)

        for news_list in category_results:
            if isinstance(news_list, Exception):
                logger.error(f"Error in search: {news_list}")
                continue

            # Filtra solo le notizie che contengono i termini di ricerca
            filtered = [
                item for item in news_list
                if any(kw in item[0].lower() for kw in keywords)
            ]
            results.extend(filtered)

        # Rimuovi duplicati e limita i risultati
        unique_results = []
        seen = set()
        for item in results:
            if item[1] not in seen:  # Controlla l'URL per evitare duplicati
                seen.add(item[1])
                unique_results.append(item)
                if len(unique_results) >= limit:
                    break

        return unique_results

    async def refresh_feeds(self):
        """Refresh all feeds periodically"""
        print("[DEBUG] Starting feed refresh background task")

        # Inizializzazione se necessario
        await self.ensure_initialized()

        while True:
            try:
                logger.info("Refreshing all news feeds...")
                print("[DEBUG] Refreshing all feeds")

                # Aggiorna i feed di tutte le categorie
                refresh_tasks = []
                for category in self.RSS_FEEDS.keys():
                    refresh_tasks.append(self.get_news(category, limit=1))

                # Esegui aggiornamento in parallelo
                await asyncio.gather(*refresh_tasks, return_exceptions=True)

                # Attendi 30 minuti prima del prossimo aggiornamento
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Error in refresh_feeds: {e}", exc_info=True)
                print(f"[ERROR] Feed refresh failed: {e}")
                # Attendi 5 minuti in caso di errore
                await asyncio.sleep(300)

    async def close(self):
        """Close the aiohttp session"""
        print("[DEBUG] Closing NewsFetcher session")
        if self.session and not self.session.closed:
            await self.session.close()
            self._initialized = False
            self.session = None


# Istanza globale
news_fetcher = NewsFetcher()


# Funzioni globali di compatibilità
async def get_news(category: str = 'generale', limit: int = 5, keywords: Optional[List[str]] = None):
    """Wrapper per compatibilità"""
    return await news_fetcher.get_news(category=category, limit=limit, keywords=keywords)


async def search_news(search_term: str, limit: int = 5):
    """Wrapper per compatibilità"""
    return await news_fetcher.search_news(search_term=search_term, limit=limit)


# Funzione di avvio per garantire che il fetcher sia inizializzato
async def start_news_fetcher():
    """Initialize the news fetcher and start background tasks"""
    await news_fetcher.initialize()
    # Optional: start background refresh
    asyncio.create_task(news_fetcher.refresh_feeds())