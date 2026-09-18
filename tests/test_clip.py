import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_clipper.fetch import NewsItem, parse_rss  # noqa: E402
from news_clipper.clip import collect, enrich_with_ai_summary, render_markdown, write_digest  # noqa: E402

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

    def test_ai_draft_is_rendered_when_present(self):
        item = NewsItem(
            title="테스트 기사",
            link="https://example.com/a",
            source="테스트",
            published=1.0,
            category="c",
            keyword="k",
            ai_core="AI가 요약한 핵심 내용입니다.",
            ai_points=["답변 포인트 1", "답변 포인트 2"],
        )
        md = render_markdown({"c": [item]}, days=1, generated_at=datetime.now(timezone.utc))

        self.assertIn("핵심 내용 (AI 초안, 원문 확인 후 수정하세요): AI가 요약한 핵심 내용입니다.", md)
        self.assertIn("면접 답변 포인트 (AI 초안):", md)
        self.assertIn("- 답변 포인트 1", md)
        self.assertIn("- 답변 포인트 2", md)


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


class EnrichWithAiSummaryTests(unittest.TestCase):
    def test_fills_ai_fields_for_top_n_when_text_and_api_key_available(self):
        item = NewsItem(
            title="테스트 기사", link="https://example.com/a", source="s", published=1.0, category="c", keyword="k"
        )
        by_category = {"c": [item]}

        with patch("news_clipper.clip.fetch_article_text", return_value="본문 " * 100), patch(
            "news_clipper.clip.summarize_batch", return_value={0: {"core": "요약", "points": ["포인트"]}}
        ):
            enrich_with_ai_summary(by_category, top_n=3)

        self.assertEqual(item.ai_core, "요약")
        self.assertEqual(item.ai_points, ["포인트"])

    def test_skips_items_with_too_little_extracted_text(self):
        item = NewsItem(
            title="테스트 기사", link="https://example.com/a", source="s", published=1.0, category="c", keyword="k"
        )
        by_category = {"c": [item]}

        with patch("news_clipper.clip.fetch_article_text", return_value="짧음"), patch(
            "news_clipper.clip.summarize_batch"
        ) as mock_summarize:
            enrich_with_ai_summary(by_category, top_n=3)

        mock_summarize.assert_called_once_with([])
        self.assertIsNone(item.ai_core)

    def test_top_n_zero_skips_entirely_without_network_calls(self):
        item = NewsItem(
            title="테스트 기사", link="https://example.com/a", source="s", published=1.0, category="c", keyword="k"
        )
        by_category = {"c": [item]}

        with patch("news_clipper.clip.fetch_article_text") as mock_fetch:
            enrich_with_ai_summary(by_category, top_n=0)

        mock_fetch.assert_not_called()
        self.assertIsNone(item.ai_core)


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
                # summarize_top_n=0: this test covers file writing, not AI drafting,
                # and would otherwise hit the real network via fetch_article_text.
                out_path = write_digest(out_dir, days=1, max_per_keyword=1, summarize_top_n=0)

            self.assertTrue(out_path.exists())
            self.assertIn("테스트 기사", out_path.read_text(encoding="utf-8"))
            index = (out_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn(out_path.stem, index)


if __name__ == "__main__":
    unittest.main()
