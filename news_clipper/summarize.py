"""AI-drafted interview notes for the day's top articles per category.

Claude fetches each article link itself via the server-side `web_fetch`
tool, so the actual page fetch happens from Anthropic's infrastructure
(not wherever this script runs) and Claude drafts only from what it reads
there - never from the headline alone. Degrades to nothing (blank note
fields via the caller) when ANTHROPIC_API_KEY is unset or the request
fails for any reason.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Dict, List, TypedDict

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5"
ANTHROPIC_VERSION = "2023-06-01"
WEB_FETCH_TOOL_TYPE = "web_fetch_20260209"


class ArticleEntry(TypedDict):
    index: int
    category: str
    title: str
    source: str
    link: str


class Summary(TypedDict):
    core: str
    points: List[str]


def _extract_json_array(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON array found in response text")
    return json.loads(match.group(0))


def summarize_batch(entries: List[ArticleEntry]) -> Dict[int, Summary]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not entries:
        return {}

    articles_block = "\n\n".join(
        f"[{e['index']}] 카테고리: {e['category']} / 출처: {e['source']}\n"
        f"제목: {e['title']}\nURL: {e['link']}"
        for e in entries
    )
    prompt = (
        "다음은 현대자동차 대외협력 직무 면접을 준비 중인 지원자를 위한 뉴스 기사 목록입니다. "
        "각 기사의 URL을 web_fetch 도구로 직접 읽은 뒤, 실제로 읽은 본문 내용에만 근거해서 "
        "(1) 핵심 내용을 2~3문장으로 요약하고 "
        "(2) 면접에서 이 기사를 언급할 때 쓸 수 있는 답변 포인트를 1~2개 bullet로 제시하세요. "
        "본문을 가져오지 못한 기사는 결과에서 제외하세요. 본문에 없는 내용을 추측해서 넣지 마세요.\n\n"
        f"{articles_block}\n\n"
        "모든 기사를 읽은 뒤, 다른 설명 없이 마지막 응답으로 아래 JSON 형식만 출력하세요: "
        '[{"index": 0, "core": "...", "points": ["...", "..."]}, ...]'
    )

    body = json.dumps(
        {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4000,
            "tools": [
                {"type": WEB_FETCH_TOOL_TYPE, "name": "web_fetch", "max_uses": len(entries) + 2}
            ],
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
        with urllib.request.urlopen(request, timeout=600) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text_blocks = [b["text"] for b in payload.get("content", []) if b.get("type") == "text"]
        if not text_blocks:
            raise ValueError(f"no text content in response: {payload}")
        parsed = _extract_json_array(text_blocks[-1])
        return {
            item["index"]: {"core": item.get("core", ""), "points": item.get("points", [])}
            for item in parsed
        }
    except Exception as exc:
        print(f"[warn] AI 요약 실패: {exc}")
        return {}
