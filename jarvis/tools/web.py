"""Web tools: DuckDuckGo search (no API key) and opening URLs."""
from __future__ import annotations

import webbrowser

try:  # the maintained package is `ddgs`; fall back to the old name
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web and return the top results. Use this for current "
                "events, facts, prices, or anything you are unsure about."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a web page or URL in the user's default browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL to open."}},
                "required": ["url"],
            },
        },
    },
]


def _web_search(args: dict, ctx) -> str:
    if DDGS is None:
        return "Web search is unavailable because the ddgs package is not installed."
    query = (args.get("query") or "").strip()
    if not query:
        return "No search query was provided."
    try:
        n = int(args.get("max_results") or ctx.config.search_results)
    except (TypeError, ValueError):
        n = ctx.config.search_results

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max(1, n)):
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            href = r.get("href", "").strip()
            results.append(f"- {title}: {body} ({href})")

    if not results:
        return f"No results found for '{query}'."
    return f"Top results for '{query}':\n" + "\n".join(results)


def _open_url(args: dict, ctx) -> str:
    url = (args.get("url") or "").strip()
    if not url:
        return "No URL was provided."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url} in the default browser."


HANDLERS = {"web_search": _web_search, "open_url": _open_url}
