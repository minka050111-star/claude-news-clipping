import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_clipper.fetch import NewsItem, parse_rss  # noqa: E402
from news_clipper.clip import collect, render_markdown, write_digest  # noqa: E402

FIXTURE = (Path(__file__).parent / "fixtures" / "sample_rss.xml").read_bytes()


class ParseRssTests(unittest.TestCase):
    def test_strips_source_suffix_and_extracts_fields(self):
        items = parse_rss(FIXTURE, category="현대차그룹 전략·사업", keyword="현대차 전략")

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "현대차, 미국 관세 대응 위해 생산라인 조정")
        self.assertEqual(items[0].source, "연합뉴스")
        self.assertTrue(items[0].link.startswith("https://news.google.com/"))
        self.assertIsNotNone(items[0].published)

    def test_ignores_items_missing_title_or_link(self):
        raw = """<?xml version="1.0"?><rss><channel>
        <item><title>제목만 있음</title></item>
        </channel></rss>""".encode("utf-8")
        items = parse_rss(raw, category="c", keyword="k")
        self.assertEqual(items, [])


class RenderMarkdownTests(unittest.TestCase):
    def test_groups_by_category_and_includes_note_placeholders(self):
        item = NewsItem(
            title="현대차그룹, 전동화 전략 발표",
            link="https://example.com/a",
            source="한국경제",
            published=datetime(2026, 9, 17, tzinfo=timezone.utc).timestamp(),
            category="현대차그룹 전략·사업",
            keyword="현대차 전략",
        )
        md = render_markdown(
            {"현대차그룹 전략·사업": [item]},
            days=1,
            generated_at=datetime.now(timezone.utc),
        )

        self.assertIn("## 현대차그룹 전략·사업", md)
        self.assertIn("[현대차그룹, 전동화 전략 발표](https://example.com/a)", md)
        self.assertIn("핵심 내용", md)
        self.assertIn("면접 답변 포인트", md)

    def test_empty_result_is_reported_clearly(self):
        md = render_markdown({}, days=1, generated_at=datetime.now(timezone.utc))
        self.assertIn("새 기사를 찾지 못했습니다", md)


class CollectTests(unittest.TestCase):
    def test_dedups_same_article_across_keywords(self):
        duplicate = NewsItem(
            title="중복 기사",
            link="https://example.com/dup",
            source="테스트",
            published=1.0,
            category="",
            keyword="",
        )

        with patch("news_clipper.clip.fetch_keyword", return_value=[duplicate]):
            by_category = collect(days=1, max_per_keyword=5, sleep_seconds=0)

        total = sum(len(items) for items in by_category.values())
        self.assertEqual(total, 1)

    def test_keyword_failure_does_not_abort_run(self):
        def flaky_fetch(keyword, category, days, limit):
            if keyword.startswith("현대"):
                raise TimeoutError("network down")
            return []

        with patch("news_clipper.clip.fetch_keyword", side_effect=flaky_fetch):
            by_category = collect(days=1, max_per_keyword=5, sleep_seconds=0)

        self.assertIn("현대차그룹 전략·사업", by_category)


class WriteDigestTests(unittest.TestCase):
    def test_writes_dated_file_and_updates_index(self):
        import tempfile

        item = NewsItem(
            title="테스트 기사",
            link="https://example.com/t",
            source="테스트",
            published=1.0,
            category="",
            keyword="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("news_clipper.clip.fetch_keyword", return_value=[item]):
                out_path = write_digest(out_dir, days=1, max_per_keyword=1)

            self.assertTrue(out_path.exists())
            self.assertIn("테스트 기사", out_path.read_text(encoding="utf-8"))
            index = (out_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn(out_path.stem, index)


if __name__ == "__main__":
    unittest.main()
