import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_clipper.summarize import (  # noqa: E402
    _resolve_google_news_link,
    fetch_article_text,
    summarize_batch,
)


class ResolveGoogleNewsLinkTests(unittest.TestCase):
    def test_extracts_meta_refresh_target(self):
        html = '<html><head><meta http-equiv="refresh" content="0;URL=\'https://real-site.com/a\'" /></head></html>'
        self.assertEqual(_resolve_google_news_link(html), "https://real-site.com/a")

    def test_returns_none_when_no_redirect_found(self):
        self.assertIsNone(_resolve_google_news_link("<html><body>no redirect here</body></html>"))


class FetchArticleTextTests(unittest.TestCase):
    def test_strips_script_and_style_tags(self):
        html = (
            "<html><body><script>var x = 1;</script>"
            "<style>.a{color:red}</style>"
            "<p>진짜 기사 본문입니다.</p></body></html>"
        )
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("news_clipper.summarize.urllib.request.urlopen", return_value=mock_response):
            text = fetch_article_text("https://example.com/a")

        self.assertIn("진짜 기사 본문입니다.", text)
        self.assertNotIn("var x", text)
        self.assertNotIn("color:red", text)

    def test_returns_empty_string_on_network_failure(self):
        with patch("news_clipper.summarize.urllib.request.urlopen", side_effect=TimeoutError("no network")):
            self.assertEqual(fetch_article_text("https://example.com/a"), "")


class SummarizeBatchTests(unittest.TestCase):
    def test_returns_empty_dict_without_api_key(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "text": "본문"}]
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(summarize_batch(entries), {})

    def test_returns_empty_dict_for_no_entries_even_with_api_key(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            self.assertEqual(summarize_batch([]), {})

    def test_parses_claude_response_into_indexed_summaries(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "text": "본문"}]
        api_response = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps([{"index": 0, "core": "요약", "points": ["포인트1"]}]),
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch(
            "news_clipper.summarize.urllib.request.urlopen", return_value=mock_response
        ):
            result = summarize_batch(entries)

        self.assertEqual(result, {0: {"core": "요약", "points": ["포인트1"]}})

    def test_returns_empty_dict_on_malformed_api_response(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "text": "본문"}]
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch(
            "news_clipper.summarize.urllib.request.urlopen", return_value=mock_response
        ):
            self.assertEqual(summarize_batch(entries), {})


if __name__ == "__main__":
    unittest.main()
