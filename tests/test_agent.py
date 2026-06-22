"""Tests for the agent tool-calling loop and tool-safety contracts.

These exercise the round-trip the unit tests in test_llm.py can't: that a model
tool call is dispatched and the result is fed back with the correct Ollama field
name (``tool_name``), and that open_application can't be turned into a shell.
"""
from types import SimpleNamespace
from unittest.mock import patch

from jarvis.agent import Jarvis
from jarvis.config import Config
from jarvis.tools import dispatch


def _make_jarvis() -> Jarvis:
    return Jarvis(Config())


def test_tool_roundtrip_uses_tool_name_field():
    jarvis = _make_jarvis()
    try:
        turns = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "get_current_time", "arguments": {}}}],
            },
            {"role": "assistant", "content": "It is noon."},
        ]
        with patch.object(jarvis.client, "chat", side_effect=turns):
            reply = jarvis.handle_text("what time is it")

        assert reply == "It is noon."
        tool_messages = [m for m in jarvis.messages if m.get("role") == "tool"]
        assert tool_messages, "expected a tool result message"
        # Ollama binds tool results by 'tool_name', not 'name'.
        assert tool_messages[0].get("tool_name") == "get_current_time"
        assert "name" not in tool_messages[0]
        assert "It is" in tool_messages[0]["content"]
    finally:
        jarvis.scheduler.stop()


def test_plain_reply_without_tools():
    jarvis = _make_jarvis()
    try:
        with patch.object(jarvis.client, "chat",
                          side_effect=[{"role": "assistant", "content": "Hello there."}]):
            assert jarvis.handle_text("hi") == "Hello there."
    finally:
        jarvis.scheduler.stop()


def test_open_application_rejects_shell_metacharacters():
    # A name crafted to break out into a second command must be refused, not run.
    out = dispatch("open_application", {"name": 'foo" & calc & "'}, SimpleNamespace())
    assert "unsafe" in out.lower()


def test_run_once_returns_and_speaks_reply():
    jarvis = _make_jarvis()
    with patch.object(jarvis.client, "chat",
                      side_effect=[{"role": "assistant", "content": "All done."}]):
        # run_once stops the scheduler itself.
        assert jarvis.run_once("do the thing") == "All done."


def test_calculator_is_registered_for_the_model():
    from jarvis.tools import tool_names

    assert "calculate" in tool_names()


def test_empty_model_turn_gets_a_fallback_reply():
    jarvis = _make_jarvis()
    try:
        with patch.object(jarvis.client, "chat",
                          side_effect=[{"role": "assistant", "content": ""}]):
            assert jarvis.handle_text("hello")  # never returns an empty string
    finally:
        jarvis.scheduler.stop()


def test_preamble_is_spoken_during_a_tool_call():
    jarvis = _make_jarvis()
    spoken = []
    jarvis.speak = lambda t: spoken.append(t)  # capture what would be voiced
    try:
        turns = [
            {"role": "assistant", "content": "Let me check the time.",
             "tool_calls": [{"function": {"name": "get_current_time", "arguments": {}}}]},
            {"role": "assistant", "content": "It is noon."},
        ]
        with patch.object(jarvis.client, "chat", side_effect=turns):
            reply = jarvis.handle_text("what time is it")
        assert "Let me check the time." in spoken
        assert reply == "It is noon."
    finally:
        jarvis.scheduler.stop()


def test_history_is_bounded():
    jarvis = _make_jarvis()
    jarvis.MAX_HISTORY = 4
    try:
        with patch.object(jarvis.client, "chat",
                          side_effect=[{"role": "assistant", "content": "ok"}] * 12):
            for i in range(8):
                jarvis.handle_text(f"msg {i}")
        assert jarvis.messages[0]["role"] == "system"   # system prompt stays pinned
        assert len(jarvis.messages) <= jarvis.MAX_HISTORY + 1
    finally:
        jarvis.scheduler.stop()
