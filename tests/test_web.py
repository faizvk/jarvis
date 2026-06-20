"""Tests for web-search hardening (DDGS is stubbed — no network)."""
from types import SimpleNamespace

from jarvis.tools import web


class _FakeDDGS:
    results: list = []
    raise_exc = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, **kwargs):
        if _FakeDDGS.raise_exc:
            raise RuntimeError("rate limited")
        return _FakeDDGS.results


def _ctx():
    return SimpleNamespace(config=SimpleNamespace(search_results=5))


def test_formats_dedupes_and_trims(monkeypatch):
    monkeypatch.setattr(web, "DDGS", _FakeDDGS)
    _FakeDDGS.raise_exc = False
    _FakeDDGS.results = [
        {"title": "A", "body": "x" * 500, "href": "http://a"},
        {"title": "A again", "body": "y", "href": "http://a"},  # duplicate URL
        {"title": "B", "body": "z", "href": "http://b"},
    ]
    out = web.HANDLERS["web_search"]({"query": "hi"}, _ctx())
    assert out.count("http://a") == 1  # deduped
    assert "http://b" in out
    assert "..." in out  # long snippet trimmed


def test_search_failure_is_soft(monkeypatch):
    monkeypatch.setattr(web, "DDGS", _FakeDDGS)
    _FakeDDGS.raise_exc = True
    out = web.HANDLERS["web_search"]({"query": "hi"}, _ctx())
    assert "couldn't" in out.lower()


def test_empty_query():
    assert "No search query" in web.HANDLERS["web_search"]({"query": ""}, _ctx())
