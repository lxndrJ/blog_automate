# websearch.py – modellunabhängige Web-Suche (kein Search-Tool des LLM).
#
# Warum: serverseitige Suche ist an Provider/Modell gebunden (Gemini-Grounding,
# Mistral web_search) und fällt bei Modellen ohne Tool-Support (z. B. Gemma)
# weg. Diese Lösung sucht direkt per HTTP – funktioniert mit JEDEM Modell.
#
# Strategien (in dieser Reihenfolge, erste nicht-leere gewinnt):
#   1. Google Programmable Search JSON API (100 Abfragen/Tag frei)
#      – braucht GOOGLE_CSE_KEY + GOOGLE_CSE_CX (Google Cloud / programmablesearchengine.google.com)
#   2. Brave Search API (Free-Tier) – braucht BRAVE_API_KEY
#   3. DuckDuckGo HTML/Lite (keylos) – klappt aus Wohn-IPs;
#      aus Cloud-IPs (GitHub Actions) meist via 202 geblockt
#   4. Wikipedia-API (keylos, zuverlässig auch aus der Cloud; de+en)
#
# Verwendung:
#   results = websearch.search("Marseille Café des Arts")   # [{'title','url','snippet'}]
#   text    = websearch.fetch_page_text(url)                # Rohtext-Auszug
#   bundle  = websearch.research_queries(["q1", "q2"])      # kompaktes Kontext-Bundle
import os
import re
import html as _html
import logging
from urllib.parse import unquote, urlparse, parse_qs, quote
import re
import html as _html
import logging
from urllib.parse import unquote, urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "de,en;q=0.7",
}

_result_cache: dict[str, list[dict]] = {}


def _unwrap(url: str) -> str:
    """DDG-Redirectlinks (…/l/?uddg=…) auf die echte URL zurückführen."""
    if "uddg=" in url:
        qs = parse_qs(urlparse(url).query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return url


def _clean(text: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _ddg_request(query: str) -> str | None:
    """DuckDuckGo abfragen – zuerst html., dann lite.-Endpoint."""
    for url, method, payload in [
        ("https://html.duckduckgo.com/html/", "POST", {"q": query}),
        ("https://lite.duckduckgo.com/lite/", "POST", {"q": query}),
        (f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}",
         "GET", None),
    ]:
        try:
            resp = requests.request(
                method, url, headers=_HEADERS, data=payload, timeout=15,
            )
            if resp.status_code == 200 and "result" in resp.text.lower():
                return resp.text
        except requests.RequestException as e:
            logger.warning("DDG-Anfrage fehlgeschlagen (%s): %s", url, e)
    return None


def _search_google_cse(query: str, max_results: int) -> list[dict]:
    """Google Programmable Search JSON API (100 Abfragen/Tag frei)."""
    key = os.getenv("GOOGLE_CSE_KEY", "").strip()
    cx = os.getenv("GOOGLE_CSE_CX", "").strip()
    if not key or not cx:
        return []
    resp = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={"key": key, "cx": cx, "q": query,
                "num": min(max_results, 10)},
        headers=_HEADERS, timeout=15,
    )
    if resp.status_code != 200:
        logger.warning("Google CSE failed (HTTP %d): %s", resp.status_code, resp.text[:200])
        return []
    return [
        {"title": item.get("title", ""), "url": item.get("link", ""),
         "snippet": _clean(item.get("htmlSnippet", ""))}
        for item in resp.json().get("items", [])
        if item.get("link")
    ]


def _search_brave(query: str, max_results: int) -> list[dict]:
    """Brave Search API (Free-Tier, braucht BRAVE_API_KEY)."""
    key = os.getenv("BRAVE_API_KEY", "").strip()
    if not key:
        return []
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": max_results},
        headers={**_HEADERS, "X-Subscription-Token": key},
        timeout=15,
    )
    if resp.status_code != 200:
        logger.warning("Brave failed (HTTP %d): %s", resp.status_code, resp.text[:200])
        return []
    return [
        {"title": item.get("title", ""), "url": item.get("url", ""),
         "snippet": _clean(item.get("description", ""))}
        for item in resp.json().get("web", {}).get("results", [])
        if item.get("url")
    ]


def _search_ddg(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo HTML/Lite Scraping (keylos).

    Aus Datacenter-IPs (CI) meist via HTTP 202 geblockt → nur Best-Effort.
    """
    page = _ddg_request(query)
    results: list[dict] = []
    if page:
        for m in re.finditer(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            page, re.S,
        ):
            url = _unwrap(_html.unescape(m.group(1)))
            title = _clean(m.group(2))
            if url.startswith("http") and title:
                results.append({"title": title, "url": url, "snippet": ""})
        snippets = [
            _clean(s) for s in re.findall(
                r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
        ]
        for i, snippet in enumerate(snippets[: len(results)]):
            results[i]["snippet"] = snippet
        if not results:
            for m in re.finditer(
                r'<a[^>]+href="(https?://[^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>',
                page, re.S,
            ):
                url = _unwrap(_html.unescape(m.group(1)))
                title = _clean(m.group(2))
                if url.startswith("http") and title:
                    results.append({"title": title, "url": url, "snippet": ""})
    return results[:max_results]


def _search_wikipedia(query: str, max_results: int) -> list[dict]:
    """Wikipedia-API (keylos, auch aus Cloud-IPs zuverlässig; de+en)."""
    results: list[dict] = []
    for lang in ("de", "en"):
        try:
            resp = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search",
                        "srsearch": query, "srlimit": max_results,
                        "srprop": "snippet", "format": "json"},
                headers=_HEADERS, timeout=15,
            )
            if resp.status_code != 200:
                continue
            for item in resp.json().get("query", {}).get("search", []):
                title = item.get("title", "")
                page_url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                results.append({
                    "title": f"{title} (Wikipedia {lang})",
                    "url": page_url,
                    "snippet": _clean(item.get("snippet", "")),
                })
        except requests.RequestException as e:
            logger.warning("Wikipedia-Suche fehlgeschlagen (%s): %s", lang, e)
    return results[:max_results]


_STRATEGIES = [
    ("google-cse", _search_google_cse),
    ("brave", _search_brave),
    ("duckduckgo", _search_ddg),
    ("wikipedia", _search_wikipedia),
]


def search(query: str, max_results: int = 8) -> list[dict]:
    """Websuche via Strategie-Kaskade. Liefert [{'title', 'url', 'snippet'}]."""
    query = (query or "").strip()
    if not query:
        return []
    if query in _result_cache:
        return _result_cache[query][:max_results]

    results: list[dict] = []
    for name, strategy in _STRATEGIES:
        try:
            results = strategy(query, max_results)
        except Exception as e:
            logger.warning("Suchstrategie '%s' fehlgeschlagen: %s", name, e)
            continue
        if results:
            logger.info("Websuche via %s: %d Treffer für %r", name, len(results), query)
            break

    _result_cache[query] = results
    if not results:
        logger.warning("Websuche ohne Treffer für: %s", query)
    return results[:max_results]


def fetch_page_text(url: str, max_chars: int = 2500) -> str:
    """Seite laden und auf Rohtext reduzieren (nur sichtbarer Inhalt)."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        page = resp.text
    except requests.RequestException as e:
        logger.info("Seitenabruf fehlgeschlagen (%s): %s", url, e)
        return ""

    page = re.sub(
        r"<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>",
        " ", page, flags=re.S | re.I,
    )
    text = re.sub(r"<[^>]+>", " ", page)
    text = _html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def research_queries(queries: list[str],
                     max_results: int = 6,
                     fetch_pages: int = 3,
                     max_chars_per_page: int = 2500) -> tuple[str, list[str]]:
    """Mehrere Suchanfragen ausführen → kontext-Bundle + Quellen-URLs.

    Liefert einen kompakten Text (Treffer + Seitenauszüge), den der
    Researcher-Agent als belegtes Material in seinen Prompt einbaut,
    plus die Liste der Quellen-URLs.
    """
    seen: set[str] = set()
    sources: list[str] = []
    blocks: list[str] = []

    for query in queries:
        results = search(query, max_results=max_results)
        for rank, r in enumerate(results, start=1):
            url = r["url"]
            if url in seen:
                continue
            seen.add(url)
            sources.append(url)
            block = f"[{len(sources)}] {r['title']}\n    {url}\n    {r['snippet']}"
            if rank <= fetch_pages:
                page_text = fetch_page_text(url, max_chars_per_page)
                if page_text:
                    block += f"\n    Auszug: {page_text}"
            blocks.append(block)

    bundle = "\n\n".join(blocks)
    return bundle, sources
