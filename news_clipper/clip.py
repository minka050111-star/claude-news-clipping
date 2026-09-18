"""Build a news clipping digest (Markdown) from configured keyword categories."""

from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .config import CATEGORIES
from .fetch import NewsItem, fetch_keyword
from .summarize import summarize_batch


def collect(days: int, max_per_keyword: int, sleep_seconds: float = 0.3) -> "OrderedDict[str, List[NewsItem]]":
    by_category: "OrderedDict[str, List[NewsItem]]" = OrderedDict()
    seen_links: set = set()
    seen_titles: set = set()

    for category in CATEGORIES:
        collected: List[NewsItem] = []
        for keyword in category.keywords:
            try:
                items = fetch_keyword(keyword, category.name, days=days, limit=max_per_keyword)
            except Exception as exc:  # a single failing keyword shouldn't kill the run
                print(f"[warn] '{keyword}' 수집 실패: {exc}")
                continue
            for item in items:
                if item.link in seen_links or item.title in seen_titles:
                    continue
                seen_links.add(item.link)
                seen_titles.add(item.title)
                collected.append(item)
            if sleep_seconds:
                time.sleep(sleep_seconds)
        collected.sort(key=lambda i: i.published or 0, reverse=True)
        by_category[category.name] = collected
    return by_category


def enrich_with_ai_summary(by_category: Dict[str, List[NewsItem]], top_n: int = 3) -> None:
    """Draft 핵심 내용/면접 답변 포인트 for the most recent `top_n` items per
    category. Claude fetches each article link itself (server-side
    web_fetch) and drafts only from what it actually reads. No-ops, leaving
    fields blank for the caller to fill in by hand, if ANTHROPIC_API_KEY is
    unset, a fetch fails, or the request otherwise fails.
    """
    if top_n <= 0:
        return

    entries = []
    index_map: Dict[int, NewsItem] = {}
    idx = 0
    for category, items in by_category.items():
        for item in items[:top_n]:
            entries.append(
                {"index": idx, "category": category, "title": item.title, "source": item.source, "link": item.link}
            )
            index_map[idx] = item
            idx += 1

    results = summarize_batch(entries)
    for i, item in index_map.items():
        if i in results:
            item.ai_core = results[i]["core"]
            item.ai_points = results[i]["points"]


def render_markdown(by_category: Dict[str, List[NewsItem]], days: int, generated_at: datetime) -> str:
    lines = [
        f"# 뉴스 클리핑 — {generated_at.strftime('%Y-%m-%d')}",
        "",
        f"_최근 {days}일 · 생성 시각 {generated_at.strftime('%Y-%m-%d %H:%M %Z')}_",
        "",
    ]

    total = sum(len(items) for items in by_category.values())
    if total == 0:
        lines.append("이번 수집에서는 새 기사를 찾지 못했습니다.")
        return "\n".join(lines) + "\n"

    for category_name, items in by_category.items():
        lines.append(f"## {category_name}")
        lines.append("")
        if not items:
            lines.append("_관련 기사 없음_")
            lines.append("")
            continue
        for item in items:
            date_str = ""
            if item.published:
                date_str = datetime.fromtimestamp(item.published, tz=timezone.utc).strftime("%m/%d")
            meta = " · ".join(p for p in [item.source, date_str] if p)
            suffix = f" ({meta})" if meta else ""
            lines.append(f"- [{item.title}]({item.link}){suffix}")
            if item.ai_core:
                lines.append(f"  - 핵심 내용 (AI 초안, 원문 확인 후 수정하세요): {item.ai_core}")
                if item.ai_points:
                    lines.append("  - 면접 답변 포인트 (AI 초안):")
                    for point in item.ai_points:
                        lines.append(f"    - {point}")
                else:
                    lines.append("  - 면접 답변 포인트: ")
            else:
                lines.append("  - 핵심 내용: ")
                lines.append("  - 면접 답변 포인트: ")
        lines.append("")
    return "\n".join(lines) + "\n"


def update_index(output_dir: Path) -> None:
    digests = sorted(output_dir.glob("20*-*-*.md"), reverse=True)
    lines = ["# 뉴스 클리핑 인덱스", "", "면접 대비용 대외협력 관련 뉴스 클리핑 기록입니다.", ""]
    for digest in digests:
        lines.append(f"- [{digest.stem}]({digest.name})")
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_digest(output_dir: Path, days: int, max_per_keyword: int, summarize_top_n: int = 3) -> Path:
    generated_at = datetime.now(timezone.utc).astimezone()
    by_category = collect(days=days, max_per_keyword=max_per_keyword)
    enrich_with_ai_summary(by_category, top_n=summarize_top_n)
    markdown = render_markdown(by_category, days=days, generated_at=generated_at)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{generated_at.strftime('%Y-%m-%d')}.md"
    out_path.write_text(markdown, encoding="utf-8")
    update_index(output_dir)
    return out_path
