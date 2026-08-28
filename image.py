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

UA = "blog.pandango.de/1.0 (https://blog.pandango.de; info@pandango.de)"

CACHE_DIR = Path(__file__).resolve().parent / "image_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_TIMEOUT = 10
PEXELS_TIMEOUT = 10
REQUEST_DELAY = 2000   # ms-Wartezeit zwischen API-Calls (Wikimedia/Unsplash Rate-Limit-Schutz)


def http(url: str, timeout: int = 20) -> dict:
    """HTTP-GET einer (bereits vollständigen) JSON-API-URL mit Retry + Backoff.

    Beachtet Wikimedia-Rate-Limits (2026):
    - Konformer User-Agent -> 200 req/min (nicht 10)
    - Retry-After Header bei 429
    - Max 3 parallele Requests (wir nutzen nur 1)
    """
    delay = 0.5  # Start mit 0.5s
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read())
            return {}
        except urllib.error.HTTPError as e:
            # Retry-After Header beachten (Wikimedia-Standard)
            retry_after = e.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = delay
            else:
                wait = delay
            
            if e.code == 429:
                print(f"    429 Too Many Requests (warte {wait:.1f}s) ...", file=sys.stderr)
            elif e.code == 403:
                print(f"    403 Forbidden (warte {wait:.1f}s) ...", file=sys.stderr)
            else:
                print(f"    HTTP {e.code} (warte {wait:.1f}s) ...", file=sys.stderr)
            
            time.sleep(wait)
            delay = min(delay * 2, 10)  # Exponential backoff, max 10s
            continue
        except Exception as ex:
            print(f"    Fehler: {ex} (warte {delay:.1f}s) ...", file=sys.stderr)
            time.sleep(delay)
            delay = min(delay * 2, 10)
            continue
    
    print(f"    ✗ Alle 5 Versuche fehlgeschlagen", file=sys.stderr)
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
        # Nur echte Foto-Dateien – keine SVGs, PDFs, Dokumente, Audio, Video
        lower_url = url.lower().split("?")[0]
        if not any(lower_url.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
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
        # Artist aus den Metadaten (für korrekte Attribution)
        artist = (ext.get("Artist") or {}).get("value", "").strip()
        return {
            "url": url,
            "source": "wikimedia",
            "license": f"Wikimedia Commons ({lic})",
            "caption": f"{topic} – Wikimedia Commons ({lic})",
            "artist": artist,
        }
    return None


def unsplash_search(query: str, orientation: str = "landscape") -> Optional[dict]:
    """Unsplash API mit Production-Tier Features (Download-Tracking + Attribution).

    Liefert {"url", "license", "caption", "photographer", "attribution",
    "download_url"} mit der Remote-Bild-URL, oder None.
    download_url wird später aufgerufen, wenn das Bild im Blog veröffentlicht wird.
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
        # Fotografen-Name + Download-Tracking-URL (für Production-Tier)
        user = r.get("user") or {}
        photographer = user.get("name", "Unknown")
        links = r.get("links") or {}
        download_url = links.get("download_location")
        # Metadaten: bevorzugt Beschreibung, sonst Alt-Text
        meta = r.get("description") or r.get("alt_description") or ""
        caption = f"{meta} – Unsplash" if meta else f"{query} – Unsplash"
        attribution = f"Photo by {photographer} on Unsplash"
        return {
            "url": img_url,
            "source": "unsplash",
            "license": "Unsplash License (frei verwendbar)",
            "caption": caption,
            "photographer": photographer,
            "attribution": attribution,
            "download_url": download_url,
        }
    return None


def pexels_search(query: str, orientation: str = "landscape") -> Optional[dict]:
    """Pexels API: Hochwertige Stockfotos mit Attribution.

    Liefert {"url", "license", "caption", "photographer", "attribution"} oder None.
    """
    if not PEXELS_KEY:
        return None
    params = urllib.parse.urlencode({
        "query": query,
        "per_page": 5,
        "orientation": orientation,
    })
    try:
        req = urllib.request.Request(
            f"https://api.pexels.com/v1/search?{params}",
            headers={
                "Authorization": PEXELS_KEY,
                "User-Agent": UA,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=PEXELS_TIMEOUT) as resp:
            if resp.status != 200:
                return None
            d = json.loads(resp.read())
    except Exception as ex:
        print(f"    Pexels-Fehler: {ex}", file=sys.stderr)
        return None

    photos = d.get("photos") or []
    for p in photos:
        src = p.get("src") or {}
        img_url = src.get("large") or src.get("large2x")
        if not img_url:
            continue
        photographer = p.get("photographer", "Unknown")
        alt = p.get("alt") or ""
        caption = f"{alt} – Pexels" if alt else f"{query} – Pexels"
        attribution = f"Photo by {photographer} on Pexels"
        return {
            "url": img_url,
            "source": "pexels",
            "license": "Pexels License (frei verwendbar)",
            "caption": caption,
            "photographer": photographer,
            "attribution": attribution,
        }
    return None


def pick_image(topic: str, orientation: str = "landscape") -> dict:
    """Bilder-Service: 1. Unsplash, 2. Pexels, 3. Wikimedia Commons (CC).

    Rückgabe: {"url", "source", "license", "caption"} – url ist die Remote-Bild-URL
    (direkt in Posts nutzbar), None wenn nichts gefunden wurde.
    """
    en_query = _en_query(topic)

    # 1. Unsplash (bevorzugt)
    us = unsplash_search(en_query, orientation)
    if us and us.get("url"):
        return us

    # 2. Pexels
    px = pexels_search(en_query, orientation)
    if px and px.get("url"):
        return px

    # 3. Wikimedia Commons (Final-Fallback)
    wm = commons_pick(topic)
    if wm and wm.get("url"):
        return wm

    return {"url": None, "source": None, "license": None, "caption": None}


if __name__ == "__main__":
    print("UNSPLASH_ACCESS_KEY:", UNSPLASH_KEY or "(nicht gesetzt)")
    print("PEXELS_API_KEY:    ", PEXELS_KEY or "(nicht gesetzt)")
    for topic in ["Markttag in Thessaloniki", "Was Valletta nachts wirklich ist", "Cacco Rom"]:
        print(f"\n[{topic}]")
        r = pick_image(topic)
        if r["url"]:
            print(f"  ✅ {r['source']} | {r['license']}")
            print(f"     photographer: {r.get('photographer', r.get('artist', '?'))}")
            print(f"     {r['url'][:100]}…")
        else:
            print("  ❌ Kein Bild")
