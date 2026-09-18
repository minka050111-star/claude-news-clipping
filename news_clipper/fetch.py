"""Fetch and parse Google News RSS search results.

No API key is required: Google News exposes a keyless RSS search endpoint
at ``https://news.google.com/rss/search``.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import List, Optional

RSS_BASE = "https://news.google.com/rss/search"
USER_AGENT = "Mozilla/5.0 (compatible; news-clipper/1.0; +interview-prep)"


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published: Optional[float]  # unix timestamp, None if unknown
    category: str
    keyword: str
    ai_core: Optional[str] = None
    ai_points: List[str] = field(default_factory=list)


def build_url(keyword: str, days: int) -> str:
    query = f"{keyword} when:{days}d"
    params = {"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}
    return f"{RSS_BASE}?{urllib.parse.urlencode(params)}"


def fetch_keyword(keyword: str, category: str, days: int, limit: int, timeout: int = 10) -> List[NewsItem]:
    url = build_url(keyword, days)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return parse_rss(raw, category=category, keyword=keyword)[:limit]


def parse_rss(raw: bytes, category: str, keyword: str) -> List[NewsItem]:
    root = ET.fromstring(raw)
    items: List[NewsItem] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else ""
        if source and title.endswith(f" - {source}"):
            title = title[: -(len(source) + 3)].strip()

        published: Optional[float] = None
        pub_date = item.findtext("pubDate")
        if pub_date:
            try:
                published = parsedate_to_datetime(pub_date).timestamp()
            except (TypeError, ValueError):
                published = None

        if title and link:
            items.append(
                NewsItem(
                    title=title,
                    link=link,
                    source=source,
                    published=published,
                    category=category,
                    keyword=keyword,
                )
            )
    return items
