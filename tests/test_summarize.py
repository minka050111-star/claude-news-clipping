import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_clipper.summarize import summarize_batch  # noqa: E402


def _mock_response(payload: dict):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    return mock_response


class SummarizeBatchTests(unittest.TestCase):
    def test_returns_empty_dict_without_api_key(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "link": "https://example.com/a"}]
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(summarize_batch(entries), {})

    def test_returns_empty_dict_for_no_entries_even_with_api_key(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            self.assertEqual(summarize_batch([]), {})

    def test_parses_final_text_block_after_web_fetch_tool_use(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "link": "https://example.com/a"}]
        # Simulates Claude calling web_fetch (tool_use + tool_result blocks)
        # before its final text-only answer.
        api_response = {
            "content": [
                {"type": "text", "text": "기사를 확인해보겠습니다."},
                {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_fetch", "input": {}},
                {"type": "web_fetch_tool_result", "tool_use_id": "srvtoolu_1", "content": {}},
                {
                    "type": "text",
                    "text": json.dumps([{"index": 0, "core": "요약", "points": ["포인트1"]}]),
                },
            ]
        }
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch(
            "news_clipper.summarize.urllib.request.urlopen", return_value=_mock_response(api_response)
        ):
            result = summarize_batch(entries)

        self.assertEqual(result, {0: {"core": "요약", "points": ["포인트1"]}})

    def test_extracts_json_array_even_with_surrounding_prose(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "link": "https://example.com/a"}]
        api_response = {
            "content": [
                {
                    "type": "text",
                    "text": "결과입니다:\n"
                    + json.dumps([{"index": 0, "core": "요약", "points": []}])
                    + "\n이상입니다.",
                }
            ]
        }
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch(
            "news_clipper.summarize.urllib.request.urlopen", return_value=_mock_response(api_response)
        ):
            result = summarize_batch(entries)

        self.assertEqual(result, {0: {"core": "요약", "points": []}})

    def test_returns_empty_dict_when_no_text_block_present(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "link": "https://example.com/a"}]
        api_response = {"content": [{"type": "server_tool_use", "id": "x", "name": "web_fetch", "input": {}}]}
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch(
            "news_clipper.summarize.urllib.request.urlopen", return_value=_mock_response(api_response)
        ):
            self.assertEqual(summarize_batch(entries), {})

    def test_returns_empty_dict_on_network_failure(self):
        entries = [{"index": 0, "category": "c", "title": "t", "source": "s", "link": "https://example.com/a"}]
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch(
            "news_clipper.summarize.urllib.request.urlopen", side_effect=TimeoutError("no network")
        ):
            self.assertEqual(summarize_batch(entries), {})


if __name__ == "__main__":
    unittest.main()
