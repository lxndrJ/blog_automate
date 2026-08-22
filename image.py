#!/usr/bin/env python3
"""image.py – Bild-Service mit Metadaten-Suche (Wikimedia Commons + Unsplash).

Strategie für gute, relevante Blog-Bilder:
  1. Wikimedia Commons: reale Fotos, nach CC-Lizenz (CC-BY/CC0/PD) gefiltert,
     Lizenz + Caption aus den Metadaten (extmetadata).
  2. Unsplash: API-Ranking nach Relevanz, Metadaten (description/alt_description)
     werden als Caption übernommen.

Alle Bilder landen im lokalen Cache (image_cache/), damit sie offline
verwendbar sind und nicht doppelt geladen werden.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()  # Lädt .env aus dem Working-Directory
except ImportError:
    pass

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

CACHE_DIR = Path(__file__).resolve().parent / "image_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_TIMEOUT = 10
REQUEST_DELAY = 500    # ms-Wartezeit zwischen API-Calls (Rate-Limit-Schutz)


def http(url: str, timeout: int = 20) -> dict:
    """HTTP-GET einer (bereits vollständigen) JSON-API-URL mit Retry + Backoff.

    Die URL wird hier NICHT gequotet – Query-Parameter müssen vorher
    sauber mit urlencode() gebildet sein.
    """
    delay = 0.0
    for _ in range(4):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read())
                if resp.status == 429:
                    time.sleep(min(delay + REQUEST_DELAY / 1000.0, 5))
                    delay *= 2
                    continue
            return {}
        except urllib.error.HTTPError as e:
            print(f"    HTTPError {e.code}", file=sys.stderr)
            time.sleep(min(delay + REQUEST_DELAY / 1000.0, 5))
            delay *= 2
            continue
        except Exception:
            time.sleep(min(delay + REQUEST_DELAY / 1000.0, 5))
            delay *= 2
            continue
    return {}


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.jpg"


def _download(url: str, timeout: int = 30) -> Optional[Path]:
    """Lädt eine Bild-URL herunter (mit Cache). Gibt Cache-Pfad oder None.

    Wichtig: Die Zwischen-Datei wird im ZIEL-Verzeichnis (CACHE_DIR) angelegt,
    nicht in /tmp – sonst schlägt os.replace() mit 'cross-device link' fehl
    (verschiedene Dateisysteme). Atomic-Rename funktioniert nur im selben FS.
    """
    cached = _cache_path(url)
    if cached.exists():
        return cached
    safe_url = urllib.parse.quote(url, safe=":/?&=%#+,")
    tmp_path = cached.with_suffix(".tmp")  # im selben Verzeichnis wie das Ziel
    try:
        req = urllib.request.Request(safe_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            with open(tmp_path, "wb") as f:
                f.write(resp.read())
        os.replace(tmp_path, cached)  # atomar, gleicher Dateibaum
        return cached
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        return None


# --- DE → EN Query-Mapping (APIs liefern auf Englisch bessere Ergebnisse) ---
_EN_MAP = {
    "Markttag": "market day",
    "Speise": "traditional food",
    "nachts": "nightlife",
    "Beruf": "tradition craftsman",
    "Wort": "language script",
    "historischer": "historic",
    "Transport": "public transport",
    "Ort": "city street",
}


def _en_query(topic: str) -> str:
    """Baut eine englische Suchquery aus einem deutschen Thema."""
    en = topic
    for de, en_ in _EN_MAP.items():
        en = en.replace(de, en_)
    return en.strip()


def commons_pick(topic: str) -> Optional[dict]:
    """Wikimedia Commons: reale Fotos, nur mit nutzbarer CC-Lizenz.

    Lizenz + Caption kommen aus den Metadaten (extmetadata.LicenseShortName).
    """
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": _en_query(topic),
        "gsrnamespace": "6",   # nur File-Namespace → echte Bilder (nicht Kategorien)
        "gsrlimit": "10",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
    }
    d = http("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    if not d:
        return None
    pages = d.get("query", {}).get("pages", {}) or {}
    for v in list(pages.values())[:10]:
        ii_list = v.get("imageinfo") or []
        if not ii_list:
            continue
        ii = ii_list[0]
        url = ii.get("url", "")
        if not url:
            continue
        # Lizenz aus den Metadaten (LicenseShortName, z. B. "CC BY-SA 4.0")
        ext = ii.get("extmetadata") or {}
        lic = (ext.get("LicenseShortName") or {}).get("value", "") or ""
        lic_norm = lic.lower().replace(" ", "")
        # Nur CC-BY/CC0/Public-Domain – sonst nichts
        if not any(tok in lic_norm for tok in ("ccby", "cc0", "publicdomain", "pd")):
            continue
        # Breite/Höhe aus Metadaten (gute Bilder, keine Icons)
        width = int((ext.get("Width") or {}).get("value", 0) or 0)
        if width and width < 400:
            continue
        return {
            "url": url,
            "source": "wikimedia",
            "license": f"Wikimedia Commons ({lic})",
            "caption": f"{topic} – Wikimedia Commons ({lic})",
        }
    return None


def unsplash_search(query: str, orientation: str = "landscape") -> Optional[dict]:
    """Unsplash: API-Ranking nach Relevanz, Metadaten als Caption.

    Liefert {"url", "license", "caption"} mit lokalem Cache-Pfad, oder None.
    """
    if not UNSPLASH_KEY:
        return None
    params = urllib.parse.urlencode({
        "client_id": UNSPLASH_KEY,
        "query": query,
        "per_page": 5,
        "orientation": orientation,
    })
    d = http(f"https://api.unsplash.com/search/photos?{params}", UNSPLASH_TIMEOUT)
    results = d.get("results") or []
    for r in results:
        urls = r.get("urls") or {}
        img_url = urls.get("raw") or urls.get("regular")
        if not img_url:
            continue
        cached = _download(img_url, 30)
        if not cached:
            continue
        # Metadaten: bevorzugt Beschreibung, sonst Alt-Text
        meta = r.get("description") or r.get("alt_description") or ""
        caption = f"{meta} – Unsplash" if meta else f"{query} – Unsplash"
        return {
            "url": str(cached),
            "source": "unsplash",
            "license": "Unsplash License (frei verwendbar)",
            "caption": caption,
        }
    return None


def pick_image(topic: str, orientation: str = "landscape") -> dict:
    """Bilder-Service: 1. Wikimedia Commons (reale Fotos, CC), 2. Unsplash.

    Rückgabe: {"url", "source", "license", "caption"} – url ist None, wenn nichts ging.
    """
    wm = commons_pick(topic)
    if wm and wm.get("url"):
        return wm

    en_query = _en_query(topic)
    us = unsplash_search(en_query, orientation)
    if us and us.get("url"):
        return us

    return {"url": None, "source": None, "license": None, "caption": None}


if __name__ == "__main__":
    print("UNSPLASH_ACCESS_KEY:", UNSPLASH_KEY or "(nicht gesetzt)")
    for topic in ["Markttag in Thessaloniki", "Was Valletta nachts wirklich ist", "Cacco Rom"]:
        print(f"\n[{topic}]")
        r = pick_image(topic)
        if r["url"]:
            print(f"  ✅ {r['source']} | {r['license']}")
            print(f"     {r['url'][:100]}…")
        else:
            print("  ❌ Kein Bild")
