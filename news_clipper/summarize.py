"""Best-effort article text extraction and AI-drafted interview notes.

Both steps degrade gracefully: if the article text can't be extracted, or
``ANTHROPIC_API_KEY`` isn't set, the caller simply gets nothing back and the
digest falls back to blank note fields for the user to fill in by hand.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, TypedDict

from .fetch import USER_AGENT

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5"
ANTHROPIC_VERSION = "2023-06-01"


class ArticleEntry(TypedDict):
    index: int
    category: str
    title: str
    source: str
    text: str


class Summary(TypedDict):
    core: str
    points: List[str]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = False
        self.chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self.chunks.append(text)


def _resolve_google_news_link(html: str) -> Optional[str]:
    match = re.search(r'content="0;\s*url=([^"]+)"', html, re.IGNORECASE)
    if match:
        return match.group(1).strip("'\"")
    match = re.search(r'href="(https?://(?!news\.google\.com)[^"]+)"', html)
    if match:
        return match.group(1)
    return None


def _fetch(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_article_text(url: str, timeout: int = 6, max_chars: int = 1500) -> str:
    try:
        html = _fetch(url, timeout)
        final_url = _resolve_google_news_link(html)
        if final_url:
            html = _fetch(final_url, timeout)

        parser = _TextExtractor()
        parser.feed(html)
        return " ".join(parser.chunks)[:max_chars]
    except Exception:
        return ""


def summarize_batch(entries: List[ArticleEntry]) -> Dict[int, Summary]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not entries:
        return {}

    articles_block = "\n\n".join(
        f"[{e['index']}] 카테고리: {e['category']} / 출처: {e['source']}\n"
        f"제목: {e['title']}\n본문 일부: {e['text']}"
        for e in entries
    )
    prompt = (
        "다음은 현대자동차 대외협력 직무 면접을 준비 중인 지원자를 위한 뉴스 기사들입니다. "
        "각 기사에 대해 (1) 핵심 내용을 2~3문장으로 요약하고, "
        "(2) 면접에서 이 기사를 언급할 때 쓸 수 있는 답변 포인트를 1~2개 bullet로 제시하세요. "
        "반드시 제공된 본문 내용에만 근거해서 작성하고, 본문에 없는 사실을 추측해서 넣지 마세요.\n\n"
        f"{articles_block}\n\n"
        "다른 설명 없이 아래 JSON 형식으로만 응답하세요: "
        '[{"index": 0, "core": "...", "points": ["...", "..."]}, ...]'
    )

    body = json.dumps(
        {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        parsed = json.loads(payload["content"][0]["text"])
        return {
            item["index"]: {"core": item.get("core", ""), "points": item.get("points", [])}
            for item in parsed
        }
    except Exception as exc:
        print(f"[warn] AI 요약 실패: {exc}")
        return {}
