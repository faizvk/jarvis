"""Tests for the Ollama client (HTTP layer mocked)."""
from unittest.mock import MagicMock, patch

import requests

from jarvis.llm import OllamaClient, OllamaError


def _resp(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.raise_for_status.return_value = None
    return m


def test_chat_returns_message_and_omits_tools_when_none():
    client = OllamaClient("http://x", "m")
    with patch("jarvis.llm.requests.post",
               return_value=_resp({"message": {"role": "assistant", "content": "hi"}})) as post:
        msg = client.chat([{"role": "user", "content": "hello"}])
    assert msg["content"] == "hi"
    assert "tools" not in post.call_args.kwargs["json"]


def test_chat_includes_tools_and_parses_tool_calls():
    client = OllamaClient("http://x", "m")
    tools = [{"type": "function", "function": {"name": "t", "parameters": {}}}]
    payload = {"message": {"tool_calls": [{"function": {"name": "t", "arguments": {}}}]}}
    with patch("jarvis.llm.requests.post", return_value=_resp(payload)) as post:
        msg = client.chat([{"role": "user", "content": "hi"}], tools=tools)
    assert msg["tool_calls"][0]["function"]["name"] == "t"
    assert post.call_args.kwargs["json"]["tools"] == tools


def test_chat_raises_on_error_payload():
    client = OllamaClient("http://x", "m")
    with patch("jarvis.llm.requests.post", return_value=_resp({"error": "boom"})):
        try:
            client.chat([])
        except OllamaError as exc:
            assert "boom" in str(exc)
        else:
            raise AssertionError("expected OllamaError")


def test_has_model_tolerates_tags():
    client = OllamaClient("http://x", "llama3.1:8b")
    with patch("jarvis.llm.requests.get", return_value=_resp({"models": [{"name": "llama3.1:8b"}]})):
        assert client.has_model() is True
    with patch("jarvis.llm.requests.get", return_value=_resp({"models": [{"name": "other:1b"}]})):
        assert client.has_model() is False


def test_is_available_false_on_connection_error():
    client = OllamaClient("http://x", "m")
    with patch("jarvis.llm.requests.get", side_effect=requests.RequestException("nope")):
        assert client.is_available() is False
