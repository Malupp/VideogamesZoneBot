# utils/news_fetcher.py
import feedparser
from urllib.parse import urlparse
from typing import List, Tuple, Dict, Optional
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class NewsFetcher:
    def __init__(self):
        self.RSS_FEEDS = {
            'generale': [
                'https://it.ign.com/feed.xml',
                'https://www.everyeye.it/feed/notizie.xml',
                'https://www.gamesource.it/feed-rss-videogiochi/',
                'https://multiplayer.it/feed/'
            ],
            'ps5': [
                'https://www.everyeye.it/rss/playstation.xml',
                'https://it.ign.com/feed/ps5',
                'https://www.mondoxbox.com/feed/'
            ],
            'xbox': [
                'https://www.everyeye.it/rss/xbox.xml',
                'https://it.ign.com/feed/xbox-series-x',
                'https://www.mondoxbox.com/feed/'
            ],
            'pc': [
                'https://www.everyeye.it/rss/pc.xml',
                'https://it.ign.com/feed/pc',
                'https://www.pcgamer.com/rss/'
            ],
            'switch': [
                'https://www.everyeye.it/rss/nintendo.xml',
                'https://it.ign.com/feed/nintendo-switch',
                'https://www.nintendolife.com/feeds/latest'
            ],
            'tech': [
                'https://www.hwupgrade.it/feed/',
                'https://www.tomshw.it/feed/'
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

    async def initialize(self):
        """Initialize aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            print("[DEBUG] Initialized aiohttp session")

    async def fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """Fetch a single RSS feed with caching"""
        print(f"[DEBUG] Fetching feed: {url}")

        # Ensure session is initialized
        if self.session is None:
            await self.initialize()

        now = datetime.now()
        if url in self.cache and now - self.last_fetch.get(url, now) < timedelta(minutes=10):
            print(f"[DEBUG] Using cached version of {url}")
            return self.cache[url]

        try:
            async with self.session.get(url) as response:
                text = await response.text()
                feed = feedparser.parse(text)
                self.cache[url] = feed
                self.last_fetch[url] = now
                print(f"[DEBUG] Successfully fetched {url}")
                return feed
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            print(f"[ERROR] Failed to fetch {url}: {e}")
            return feedparser.FeedParserDict()

    async def get_news(self, category: str = 'generale', limit: int = 5, keywords: Optional[List[str]] = None) -> List[Tuple[str, str, str]]:
        """Get news from multiple sources with optional keyword filtering"""
        print(f"[DEBUG] Getting news for category: {category}, limit: {limit}")

        try:
            urls = self.RSS_FEEDS.get(category, [])
            if not urls:
                print(f"[WARNING] No URLs found for category: {category}")
                return []

            tasks = [self.fetch_feed(url) for url in urls]
            results = await asyncio.gather(*tasks)

            all_entries = []
            for feed, url in zip(results, urls):
                domain = urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()
                for entry in feed.entries[:limit * 2]:
                    title = entry.title
                    link = entry.link
                    published = getattr(entry, 'published_parsed', None)

                    # Aggiunto filtro per keywords
                    if keywords and not any(kw.lower() in title.lower() for kw in keywords):
                        continue

                    all_entries.append((title, link, domain, published))

            all_entries.sort(key=lambda x: x[3] or datetime.min, reverse=True)

            unique_entries = []
            seen = set()
            for entry in all_entries:
                if entry[1] not in seen:
                    seen.add(entry[1])
                    unique_entries.append(entry[:3])
                if len(unique_entries) >= limit:
                    break

            print(f"[DEBUG] Returning {len(unique_entries)} news items")
            return unique_entries

        except Exception as e:
            logger.error(f"Error in get_news: {e}")
            print(f"[ERROR] Failed to get news: {e}")
            return []

    async def search_news(self, search_term: str, limit: int = 5) -> List[Tuple[str, str, str]]:
        """Search news across all categories"""
        print(f"[DEBUG] Searching for: {search_term}")

        results = []
        keywords = search_term.lower().split()

        for category in self.RSS_FEEDS.keys():
            try:
                # Ottieni le notizie per la categoria corrente
                news = await self.get_news(category, limit * 2)

                # Filtra le notizie che contengono i termini di ricerca
                filtered = [
                    item for item in news
                    if any(kw in item[0].lower() for kw in keywords)
                ]
                results.extend(filtered)

            except Exception as e:
                logger.error(f"Error searching {category}: {e}")

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

        # Initialize session if needed
        if self.session is None:
            await self.initialize()

        while True:
            try:
                logger.info("Refreshing all news feeds...")
                print("[DEBUG] Refreshing all feeds")
                for category in self.RSS_FEEDS.keys():
                    await self.get_news(category, limit=1)
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Error in refresh_feeds: {e}")
                print(f"[ERROR] Feed refresh failed: {e}")
                await asyncio.sleep(600)  # Wait longer if error occurs

    async def close(self):
        """Close the aiohttp session"""
        print("[DEBUG] Closing NewsFetcher session")
        if self.session:
            await self.session.close()
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