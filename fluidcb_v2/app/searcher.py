# ── searcher.py ───────────────────────────────────────────────────────────────
# DuckDuckGo search + page fetch for /search trigger.
# Drop-in replaceable with SearXNG later — just swap _raw_search().
#
# Public API:
#   search(query, max_results=5) -> str   formatted context block for the model
#   is_search_command(text)      -> bool  True if message starts with /search

import re
import textwrap
from typing import Optional


# ── Trigger detection ──────────────────────────────────────────────────────────

def is_search_command(text: str) -> bool:
    return text.strip().lower().startswith("/search ")

def extract_query(text: str) -> str:
    """Strips /search prefix and returns the raw query."""
    return text.strip()[8:].strip()   # len("/search ") == 8


# ── Search ─────────────────────────────────────────────────────────────────────

def _raw_search(query: str, max_results: int) -> list[dict]:
    """
    Runs a DDG text search. Returns list of {title, href, body}.
    Falls back to empty list on any error so the caller always gets something.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except ImportError:
        print("[searcher] duckduckgo_search not installed — run: pip install duckduckgo-search")
        return []
    except Exception as e:
        print(f"[searcher] DDG search error: {e}")
        return []


def _fetch_page(url: str, max_chars: int = 2000) -> Optional[str]:
    """
    Fetches a URL and extracts readable text.
    Returns None if fetch fails or content is too short to be useful.
    """
    try:
        import requests
        from html.parser import HTMLParser

        resp = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (compatible; FluidCB/1.0)"
        })
        resp.raise_for_status()

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.chunks: list[str] = []
                self._skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = False

            def handle_data(self, data):
                if not self._skip:
                    stripped = data.strip()
                    if len(stripped) > 20:
                        self.chunks.append(stripped)

        parser = _TextExtractor()
        parser.feed(resp.text)
        raw = " ".join(parser.chunks)

        # Collapse whitespace
        raw = re.sub(r"\s+", " ", raw).strip()

        if len(raw) < 100:
            return None

        return raw[:max_chars]

    except Exception:
        return None


# ── Result formatter ───────────────────────────────────────────────────────────

def _is_reddit(url: str) -> bool:
    return "reddit.com" in url

def _format_results(results: list[dict], fetched: dict[str, str]) -> str:
    """Builds a clean context block the model can read."""
    if not results:
        return "No results found for this query."

    lines = []
    for i, r in enumerate(results, 1):
        url   = r.get("href", "")
        title = r.get("title", "").strip()
        body  = r.get("body", "").strip()
        page  = fetched.get(url, "")

        lines.append(f"[{i}] {title}")
        lines.append(f"    URL: {url}")

        # For Reddit — the body snippet usually has the comments/text we want
        if _is_reddit(url) and body:
            lines.append(f"    {body}")
        elif page:
            # Use fetched page content (richer than snippet)
            trimmed = textwrap.shorten(page, width=400, placeholder="…")
            lines.append(f"    {trimmed}")
        elif body:
            lines.append(f"    {body}")

        lines.append("")

    return "\n".join(lines)


# ── Public search function ─────────────────────────────────────────────────────

def search(query: str, max_results: int = 6, fetch_pages: bool = True) -> str:
    """
    Searches DDG, optionally fetches top pages, returns a formatted context block.

    Reddit queries: bumps max_results and prioritises reddit.com results.
    Regular queries: fetches top 2 pages for richer content.
    """
    # Detect reddit intent and adjust query
    reddit_mode = "reddit" in query.lower()
    if reddit_mode and "reddit" not in query.lower().split()[0]:
        # Ensure reddit is included in the search
        pass
    if reddit_mode:
        max_results = max(max_results, 8)

    raw = _raw_search(query, max_results)

    if not raw:
        return f"Search returned no results for: {query}"

    # Sort: reddit results first if in reddit mode
    if reddit_mode:
        raw = sorted(raw, key=lambda r: 0 if _is_reddit(r.get("href", "")) else 1)

    # Fetch top non-reddit pages for richer content
    fetched: dict[str, str] = {}
    if fetch_pages:
        fetch_targets = [r for r in raw if not _is_reddit(r.get("href", ""))][:2]
        for r in fetch_targets:
            url = r.get("href", "")
            if url:
                content = _fetch_page(url)
                if content:
                    fetched[url] = content

    return _format_results(raw[:max_results], fetched)
