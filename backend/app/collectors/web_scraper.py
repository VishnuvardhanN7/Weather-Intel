import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.services.weather_service import weather_service
from app.models.weather_event import EventSource

logger = logging.getLogger(__name__)

INDIAN_NEWS_SOURCES = [
    {
        "name": "NDTV Weather",
        "base_url": "https://www.ndtv.com",
        "weather_path": "/weather",
        "selectors": {
            "article_list": "div.Nwsstrt-sm436_Nwsstrt-sm436__BXIxO, div.story__card, article.cnt-lst-itm",
            "title": "h2 a, h3 a, .story__title a, .nws_title",
            "link": "h2 a, h3 a, .story__title a, .nws_title",
            "description": "p, .story__desc, .nws_desc, .story__content",
        },
    },
    {
        "name": "The Hindu Weather",
        "base_url": "https://www.thehindu.com",
        "weather_path": "/topic/weather",
        "selectors": {
            "article_list": "div.story-card, article.story, div:nth-of-type(1)",
            "title": "h3 a, h2 a, .title",
            "link": "h3 a, h2 a, .title",
            "description": "p.intro, .story-text, .summary",
        },
    },
    {
        "name": "India Today Weather",
        "base_url": "https://www.indiatoday.in",
        "weather_path": "/weather",
        "selectors": {
            "article_list": "div.bx, div.card, article",
            "title": "h2 a, h3 a, .title a, .btm_hed a",
            "link": "h2 a, h3 a, .title a, .btm_hed a",
            "description": "p, .description, .short",
        },
    },
    {
        "name": "Times of India Weather",
        "base_url": "https://timesofindia.indiatimes.com",
        "weather_path": "/topic/weather-news",
        "selectors": {
            "article_list": "div.w_panel div, div[data-articleid], .article-list li",
            "title": "h2 a, h3 a, .w_tit a, .title",
            "link": "h2 a, h3 a, .w_tit a, .title",
            "description": "p, .w_txt, .synopsis",
        },
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

WEATHER_KEYWORDS = [
    "rain", "rainfall", "storm", "thunderstorm", "flood", "flooding",
    "cyclone", "hurricane", "heatwave", "cold wave", "fog", "dust storm",
    "wind", "heavy rain", "downpour", "monsoon", "drought", "hail",
    "lightning", "landslide", "weather", "IMD", "meteorological", "forecast"
]

def is_valid_article_image(url: Optional[str]) -> bool:
    if not url or not isinstance(url, str):
        return False
    url_lower = url.lower()
    if url_lower.startswith("data:"):
        return False
    forbidden = [
        "logo", "icon", "avatar", "tracking", "pixel", "1x1", "sprite",
        "button", "ad-", "banner", "placeholder", ".svg", "default-user",
        "favicon", "share", "social"
    ]
    if any(bad in url_lower for bad in forbidden):
        return False
    return True


class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _is_weather_related(self, text: str) -> bool:
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in WEATHER_KEYWORDS)

    def _extract_location_from_text(self, text: str) -> Dict:
        from app.collectors.twitter_collector import INDIAN_STATES_AND_CITIES
        text_lower = text.lower()
        for city_key in INDIAN_STATES_AND_CITIES:
            if city_key in text_lower:
                city, state = INDIAN_STATES_AND_CITIES[city_key]
                from app.utils.geolocation import get_city_coordinates
                coords = get_city_coordinates(city)
                return {
                    "city": city,
                    "state": state,
                    "latitude": coords.get("latitude"),
                    "longitude": coords.get("longitude"),
                }
        return {"city": "India", "state": "India", "latitude": 20.5937, "longitude": 78.9629}

    def fetch_page_og_image(self, article_url: str) -> Optional[str]:
        if not article_url or not article_url.startswith("http"):
            return None
        try:
            resp = self.session.get(article_url, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                # 1. og:image & twitter:image
                for meta in soup.find_all("meta"):
                    prop = (meta.get("property") or meta.get("name") or "").lower()
                    if prop in ("og:image", "twitter:image", "twitter:image:src", "image", "og:image:secure_url"):
                        content = meta.get("content")
                        if is_valid_article_image(content):
                            return urljoin(article_url, content)

                # 2. JSON-LD structured image
                import json
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "{}")
                        if isinstance(data, list) and data:
                            data = data[0]
                        if isinstance(data, dict):
                            img = data.get("image")
                            if isinstance(img, str) and is_valid_article_image(img):
                                return urljoin(article_url, img)
                            elif isinstance(img, list) and img and isinstance(img[0], str) and is_valid_article_image(img[0]):
                                return urljoin(article_url, img[0])
                            elif isinstance(img, dict) and img.get("url") and is_valid_article_image(img.get("url")):
                                return urljoin(article_url, img.get("url"))
                    except Exception:
                        pass
        except Exception as err:
            logger.debug(f"Deep og:image fetch note: {err}")
        return None

    def scrape_source(self, source: Dict) -> List[dict]:
        articles = []
        url = urljoin(source["base_url"], source["weather_path"])
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return []
            soup = BeautifulSoup(response.content, "html.parser")
            article_elements = soup.select(source["selectors"]["article_list"])

            for article_el in article_elements[:10]:
                try:
                    title_el = article_el.select_one(source["selectors"]["title"])
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    link = title_el.get("href", "")
                    if link and not link.startswith("http"):
                        link = urljoin(source["base_url"], link)

                    desc_el = article_el.select_one(source["selectors"]["description"])
                    description = desc_el.get_text(strip=True) if desc_el else title

                    if not self._is_weather_related(title + " " + description):
                        continue

                    img_url = None
                    img_el = article_el.select_one("img")
                    if img_el:
                        raw_src = img_el.get("src") or img_el.get("data-src") or img_el.get("data-original")
                        if raw_src:
                            candidate = urljoin(source["base_url"], raw_src)
                            if is_valid_article_image(candidate):
                                img_url = candidate

                    if not img_url and link:
                        img_url = self.fetch_page_og_image(link)

                    location = self._extract_location_from_text(title + " " + description)
                    photos = [img_url] if img_url else []
                    media = [{"type": "image", "url": img_url, "thumbnail_url": img_url, "source_url": link}] if img_url else []

                    articles.append({
                        "title": title,
                        "description": description,
                        "source_url": link,
                        "source_name": source["name"],
                        "city": location["city"],
                        "state": location["state"],
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                        "photos": photos,
                        "media": media,
                        "metadata": {
                            "source_name": source["name"],
                            "image_url": img_url,
                            "media": media,
                        },
                        "reported_at": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    continue
        except Exception as e:
            logger.debug(f"Error scraping {source['name']}: {e}")

        return articles

    def scrape_rss_feeds(self) -> List[dict]:
        rss_urls = [
            ("Google News India Weather", "https://news.google.com/rss/search?q=India+weather+rainfall+flood+IMD&hl=en-IN&gl=IN&ceid=IN:en"),
            ("Times of India Weather", "https://timesofindia.indiatimes.com/rssfeeds/2647163.cms"),
            ("Indian Express India", "https://indianexpress.com/section/india/feed/"),
            ("IMD Bulletins", "https://mausam.imd.gov.in/responsive/rss_district_nowcast.php")
        ]
        articles = []
        for name, url in rss_urls:
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.content, "xml")
                    items = soup.find_all("item")
                    for item in items[:10]:
                        title = item.find("title").get_text(strip=True) if item.find("title") else "Weather News"
                        link = item.find("link").get_text(strip=True) if item.find("link") else url
                        raw_desc = item.find("description").get_text(strip=True) if item.find("description") else title
                        
                        desc_soup = BeautifulSoup(raw_desc, "html.parser")
                        clean_desc = desc_soup.get_text(strip=True)

                        if not self._is_weather_related(title + " " + clean_desc):
                            continue
                        
                        img_url = None
                        
                        # 1. media:content / media:thumbnail
                        media_content = item.find("media:content") or item.find("media:thumbnail")
                        if media_content and media_content.get("url"):
                            candidate = media_content.get("url")
                            if is_valid_article_image(candidate):
                                img_url = candidate

                        # 2. enclosure
                        if not img_url:
                            enc = item.find("enclosure")
                            if enc and enc.get("url") and "image" in enc.get("type", ""):
                                candidate = enc.get("url")
                                if is_valid_article_image(candidate):
                                    img_url = candidate

                        # 3. <img> in description HTML
                        if not img_url:
                            img_tag = desc_soup.find("img")
                            if img_tag and img_tag.get("src"):
                                candidate = img_tag.get("src")
                                if is_valid_article_image(candidate):
                                    img_url = candidate

                        # 4. Deep og:image fetch if link exists
                        if not img_url and link and link.startswith("http"):
                            img_url = self.fetch_page_og_image(link)

                        location = self._extract_location_from_text(title + " " + clean_desc)
                        photos = [img_url] if img_url else []
                        media = [{"type": "image", "url": img_url, "thumbnail_url": img_url, "source_url": link}] if img_url else []

                        articles.append({
                            "title": title,
                            "description": clean_desc or title,
                            "source_url": link,
                            "source_name": name,
                            "city": location["city"],
                            "state": location["state"],
                            "latitude": location["latitude"],
                            "longitude": location["longitude"],
                            "photos": photos,
                            "media": media,
                            "metadata": {
                                "source_name": name,
                                "image_url": img_url,
                                "media": media,
                            },
                            "reported_at": datetime.utcnow().isoformat(),
                        })
            except Exception as e:
                logger.debug(f"RSS feed {name} fetch note: {e}")
        return articles

    async def scrape_all_sources(self) -> List[dict]:
        all_articles = []
        for source in INDIAN_NEWS_SOURCES:
            articles = self.scrape_source(source)
            all_articles.extend(articles)
        
        rss_articles = self.scrape_rss_feeds()
        all_articles.extend(rss_articles)
        
        logger.info(f"Total articles scraped: {len(all_articles)}")
        return all_articles

    async def store_scraped_articles(self, db, articles: List[dict]):
        stored_count = 0
        for article in articles:
            try:
                photos = article.get("photos", [])
                videos = article.get("videos", [])
                metadata = article.get("metadata", {})

                await weather_service.ingest_event(
                    db=db,
                    title=article["title"],
                    description=article["description"],
                    source=EventSource.WEB,
                    source_url=article.get("source_url"),
                    city=article.get("city"),
                    state=article.get("state"),
                    latitude=article.get("latitude"),
                    longitude=article.get("longitude"),
                    photos=photos,
                    videos=videos,
                    metadata=metadata,
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing article: {e}")
        logger.info(f"Stored {stored_count} articles in database")
        return stored_count


web_scraper = WebScraper()