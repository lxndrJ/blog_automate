# publisher.py – Markdown + ehrliches Frontmatter schreiben
import os
import re
import sys
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    BERLIN_TZ = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover - Fallback ohne zoneinfo
    from datetime import timezone, timedelta
    BERLIN_TZ = timezone(timedelta(hours=2), name="+0200")

from config import POSTS_DIR


def _now_berlin() -> datetime:
    """Aktuelle Zeit in der Zone Europe/Berlin (inkl. Sommerzeit)."""
    return datetime.now(BERLIN_TZ)


def post_timestamp() -> str:
    """Publikationszeitstempel: exakter Erzeugungszeitpunkt in Berlin-Zone.

    Jeder Post erhält den tatsächlichen Erzeugungszeitpunkt – das garantiert
    eindeutige Timestamps auch bei mehreren Posts am selben Tag und einen
    sauber sortierbaren RSS-Feed.
    """
    return _now_berlin().strftime("%Y-%m-%d %H:%M:%S %z")


def _find_image(topic: str, category: str = "") -> dict | None:
    """Automatische Bildsuche (Unsplash/Wikimedia) – nie fatal, nur Fallback.
    
    Nutzt kategorie-spezifische Suchstrategien:
    - Work-Life Balance: allgemeine, ästhetische Bilder (Natur, Ruhe, Lifestyle)
    - Kochen/Essen: Richtung Rezepte (Zutaten, Zubereitung, fertiges Gericht)
    - Reise (Default): Titel-basierte Suche wie bisher
    """
    try:
        from image import unsplash_search, commons_pick
    
        # ── Kategorie-spezifische Suchstrategien ──
        cat_lower = category.lower().replace(" ", "")
        
        if "worklife" in cat_lower or "work-life" in category.lower():
            # Allgemeine, ästhetische Bilder statt spezifischer Titel-Suche
            queries = [
                "work life balance nature",
                "relaxation lifestyle calm",
                "wellness peaceful morning",
                "nature walking peaceful",
                "cozy home lifestyle",
            ]
        elif "kochen" in cat_lower or "essen" in cat_lower:
            # Richtung Rezepte: Zutaten, Zubereitung, fertiges Gericht
            queries = [
                "recipe homemade food",
                "cooking ingredients kitchen",
                "homemade dish preparation",
                "baking fresh bread",
                "healthy meal plate",
            ]
        else:
            # Reise / Default: Titel-basierte Suche
            stop_words = {'der', 'die', 'das', 'ein', 'eine', 'einen', 'und', 'oder',
                         'in', 'an', 'auf', 'für', 'mit', 'von', 'zu', 'bei',
                         'warum', 'wie', 'was', 'wenn', 'dass', 'als', 'auch',
                         'nicht', 'nie', 'mehr', 'sehr', 'fast', 'wirklich',
                         'uns', 'unsere', 'meine', 'ich', 'mir', 'mich'}
            words = re.findall(r'[a-zA-ZäöüÄÖÜß]{4,}', topic.lower())
            keywords = [w for w in words if w not in stop_words][:5]
            
            queries = []
            if keywords:
                queries.append(' '.join(keywords[:3]))
                queries.append(' '.join(keywords[:2]))
            queries.append(topic[:40])
        
        for q in queries:
            r = unsplash_search(q)
            if r and r.get("url"):
                return r
        
        # Wikimedia-Fallback
        for q in queries:
            r = commons_pick(q)
            if r and r.get("url"):
                return r
    except Exception as e:
        print(f"      (Bildsuche fehlgeschlagen: {e})", file=sys.stderr)
    return None


def _yaml_escape(s: str) -> str:
    """Sichere YAML-String-Escaping für Front-Matter."""
    s = s.replace('"', '\\"')
    s = s.replace('\n', ' ')
    s = s.replace('\r', '')
    return s


def _safe_filename(title: str) -> str:
    t = title.lower().replace("&", "und")
    t = re.sub(r"[^a-z0-9äöüß \-]+", "", t)
    return re.sub(r"[\s]+", "-", t).strip("-")[:80]


def save(title: str, content: str, image_url: str | None, sources: list[str],
         image_meta: dict | None = None, category: str = "Reise") -> str:
    """Schreibt einen Blog-Post mit korrektem Frontmatter nach POSTS_DIR.

    Args:
        title:     Post-Titel
        content:   Markdown-Body
        image_url: Direkte Bild-URL (Optional, wird sonst automatisch gesucht)
        sources:   Liste der Quellen-URLs
        image_meta: Metadaten-Dict von image.pick_image() mit 'source',
                    'photographer', 'attribution', 'license' etc.
        category:  Jekyll-Kategorie (z. B. "Reise", "Kochen/Essen", "Work-Life Balance")
    """
    os.makedirs(POSTS_DIR, exist_ok=True)
    now = _now_berlin()
    date_str = now.strftime("%Y-%m-%d")
    date_full = post_timestamp()
    slug = _safe_filename(title)
    filename = f"{POSTS_DIR}/{date_str}-{slug}.md"

    # Bild: übergebenes zuerst, sonst automatisch suchen
    if not image_url:
        print("      → Bild automatisch gesucht …")
        img = _find_image(title, category=category)
        if img:
            image_url = img["url"]
            image_meta = img
            print(f"      → Bild: {img['source']} ({img['license']})")

    # Permalink (explizit, unabhängig von Jekyll-Config)
    permalink = f"/{now.strftime('%Y/%m/%d')}/{slug}.html"

    # Bild-Credit für das Layout (image_credit)
    image_credit = None
    if image_meta:
        if image_meta.get("attribution"):
            image_credit = image_meta["attribution"]
        elif image_meta.get("photographer"):
            image_credit = f"Photo by {image_meta['photographer']}"
        elif image_meta.get("source") == "wikimedia":
            artist = image_meta.get("artist", "").strip()
            if artist:
                image_credit = f"Bild: {artist} (Wikimedia Commons, {image_meta.get('license', '')})"
            else:
                image_credit = f"Bild: {image_meta.get('license', 'Wikimedia Commons')}"
        elif image_meta.get("license"):
            image_credit = f"Bild: {image_meta['license']}"

    # Frontmatter
    fm = [
        "---",
        "layout: post",
        f"categories: [{category}]",

        f'title: "{_yaml_escape(title)}"',
        f'date: {date_full}',
        f'permalink: {permalink}',
        "author: lxndrJ",
        "ai_assisted: true",
    ]
    if image_url:
        fm.append(f"image: {image_url}")
    if image_credit:
        fm.append(f'image_credit: "{_yaml_escape(image_credit)}"')
    if sources:
        fm.append("sources:")
        fm.extend(f"  - {s}" for s in sources)
    fm.append("---")

    # Body – KEIN Hero-Bild mehr (das Layout rendert es)
    body = content.strip() + "\n"

    # Quellen-Sektion sicherstellen (Editor soll sie anlegen; Fallback)
    if sources and "## Quellen" not in content:
        body += "\n## Quellen\n\n" + "\n".join(f"- <{s}>" for s in sources) + "\n"
    else:
        # Bestehende Quellen: Plain-Text-URLs → Markdown-Links konvertieren
        body = re.sub(
            r'^(\s*-\s+)(.+?)[,\s]+(https?://\S+)\s*$',
            r'\1[\2](\3)',
            body,
            flags=re.MULTILINE
        )
        # Multi-Line: '- Text\n  https://url' → '- [Text](https://url)'
        body = re.sub(
            r'^- (.+?)\n  (https?://\S+)\s*$',
            r'- [\1](\2)',
            body,
            flags=re.MULTILINE
        )

    # Transparenz-Hinweis ans Ende, falls nicht vorhanden
    if "KI" not in body[-200:]:
        body += (
            "\n---\n\n*Dieser Beitrag wurde KI-gestützt geschrieben "
            "und von lxndrJ kuratiert, geprüft und veröffentlicht.*\n"
        )

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(fm) + "\n" + body)
    return filename
