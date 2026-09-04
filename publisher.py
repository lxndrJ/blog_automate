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


def _find_image(topic: str, category: str = "", image_query: str = "") -> dict | None:
    """Automatische Bildsuche (Unsplash → Pexels → Wikimedia) – nie fatal, nur Fallback.
    
    Strategie:
    1. image_query (Englisch, vom Topic-Generator) als PRIMÄRE Suchbegriff
    2. Kategorie-spezifische Fallback-Queries
    3. Wikimedia Commons als letzter Rückfall
    """
    try:
        from image import unsplash_search, pexels_search, commons_pick
        
        # ── Primäre Query: englische image_query vom Topic-Generator ──
        queries = []
        if image_query:
            queries.append(image_query)  # Beste Query zuerst
        
        # ── Kategorie-spezifische Fallback-Queries ──
        cat_lower = category.lower().replace(" ", "")
        
        if "worklife" in cat_lower or "work-life" in category.lower():
            queries.extend([
                "work life balance nature",
                "relaxation lifestyle calm",
                "wellness peaceful morning",
            ])
        elif "kochen" in cat_lower or "essen" in cat_lower:
            queries.extend([
                "recipe homemade food",
                "cooking ingredients kitchen",
                "homemade dish preparation",
            ])
        else:
            # Reise / Default: zusätzliche Keywords aus dem Titel
            stop_words = {'der', 'die', 'das', 'ein', 'eine', 'einen', 'und', 'oder',
                         'in', 'an', 'auf', 'für', 'mit', 'von', 'zu', 'bei',
                         'warum', 'wie', 'was', 'wenn', 'dass', 'als', 'auch',
                         'nicht', 'nie', 'mehr', 'sehr', 'fast', 'wirklich',
                         'uns', 'unsere', 'meine', 'ich', 'mir', 'mich'}
            words = re.findall(r'[a-zA-ZäöüÄÖÜß]{4,}', topic.lower())
            keywords = [w for w in words if w not in stop_words][:4]
            if keywords:
                queries.append(' '.join(keywords[:3]))
        
        # Dedup + Max 5 Queries
        seen = set()
        unique_queries = []
        for q in queries:
            q = q.strip()
            if q and q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)
        queries = unique_queries[:5]
        
        # ── Kette: Unsplash → Pexels → Wikimedia ──
        for q in queries:
            r = unsplash_search(q)
            if r and r.get("url"):
                return r
        
        for q in queries:
            r = pexels_search(q)
            if r and r.get("url"):
                return r
        
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


def _enforce_link_limit(body: str, max_links: int = 5) -> str:
    """Reduziert externe Links im Body auf max_links.

    Strategie:
    - Zählt alle externen Links (Markdown [text](url) mit http/https URL)
    - Behält die ERSTEN max_links Vorkommen (die relevantesten stehen meist oben)
    - Entfernt überschüssige Links: im Quellen-Bereich → Zeile streichen,
      im Fließtext → Link-Auszeichnung entfernen (Text bleibt, URL weg)
    """
    # Alle externen Markdown-Links finden (mit Position)
    link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
    all_links = list(link_pattern.finditer(body))
    
    if len(all_links) <= max_links:
        return body
    
    print(f"      → Link-Limit: {len(all_links)} Links gefunden, reduziere auf {max_links}")
    
    # Links die behalten werden (die ersten max_links)
    keep_spans = set()
    for m in all_links[:max_links]:
        keep_spans.add((m.start(), m.end()))
    
    # Überschüssige Links entfernen
    result = []
    last_end = 0
    for i, m in enumerate(all_links):
        if (m.start(), m.end()) in keep_spans:
            result.append(body[last_end:m.end()])
            last_end = m.end()
        else:
            # Text vor diesem Link übernehmen
            result.append(body[last_end:m.start()])
            # Link-Text ohne URL behalten (im Fließtext) oder Zeile streichen (Quellen)
            link_text = m.group(1).strip()
            # Prüfen ob es eine Quellen-Zeile ist (Liste mit - oder *)
            line_start = body.rfind('\n', 0, m.start()) + 1
            line_content = body[line_start:m.start()].strip()
            if line_content.startswith('-') or line_content.startswith('*'):
                # Quellen-Eintrag → komplette Zeile streichen
                pass  # nichts hinzufügen, letzte Zeile wird übersprungen
            else:
                # Fließtext → nur den Text behalten, Link-Auszeichnung entfernen
                result.append(link_text)
            last_end = m.end()
    
    result.append(body[last_end:])
    return ''.join(result)


def _extract_description(content: str, max_len: int = 160) -> str:
    """Ersten sinnvollen Absatz als description/Teaser extrahieren.

    Springt über H1-Überschrift, leere Zeilen und Markdown-Formatierung.
    Liefert max. max_len Zeichen (am Wortende abgeschnitten).
    """
    lines = content.strip().splitlines()
    # Erste Nicht-Überschrift, nicht-leere Zeile finden
    first_text = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("---"):
            continue
        if stripped.startswith("```"):
            continue
        first_text = stripped
        break

    if not first_text:
        return ""

    # Markdown-Formatierung entfernen (Links, Bold, Italic)
    import re as _re
    clean = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', first_text)
    clean = _re.sub(r'\*\*([^*]+)\*\*', r'\1', clean)
    clean = _re.sub(r'\*([^*]+)\*', r'\1', clean)
    clean = _re.sub(r'`([^`]+)`', r'\1', clean)
    clean = clean.strip()

    # Auf max_len kürzen (am letzten Wortende)
    if len(clean) > max_len:
        cut = clean[:max_len]
        last_space = cut.rfind(' ')
        if last_space > max_len // 2:
            cut = cut[:last_space]
        clean = cut.rstrip() + "…"

    return clean


def save(title: str, content: str, image_url: str | None, sources: list[str],
         image_meta: dict | None = None, category: str = "Reise",
         image_query: str = "") -> str:
    """Schreibt einen Blog-Post mit korrektem Frontmatter nach POSTS_DIR.

    Args:
        title:       Post-Titel
        content:     Markdown-Body
        image_url:   Direkte Bild-URL (Optional, wird sonst automatisch gesucht)
        sources:     Liste der Quellen-URLs
        image_meta:  Metadaten-Dict von image.pick_image() mit 'source',
                     'photographer', 'attribution', 'license' etc.
        category:    Jekyll-Kategorie (z. B. "Reise", "Kochen/Essen", "Work-Life Balance")
        image_query: Englische Suchquery für die Bildsuche (vom Topic-Generator)
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
        if image_query:
            print(f"         Query: {image_query}")
        img = _find_image(title, category=category, image_query=image_query)
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

    # Description/Teaser für die Homepage-Liste
    description = _extract_description(content)

    # Frontmatter
    fm = [
        "---",
        "layout: post",
        f"categories: [{category}]",

        f'title: "{_yaml_escape(title)}"',
    ]
    if description:
        fm.append(f'description: "{_yaml_escape(description)}"')
    fm.extend([
        f'date: {date_full}',
        f'permalink: {permalink}',
        "author: lxndrJ",
        "ai_assisted: true",
    ])
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

    # ── Link-Limit: max 5 externe Links im Body (inkl. Quellen) ──
    body = _enforce_link_limit(body, max_links=5)

    # Transparenz-Hinweis + Link-Disclaimer ans Ende
    if "KI" not in body[-300:]:
        body += (
            "\n---\n\n*Dieser Beitrag wurde KI-gestützt geschrieben "
            "und von lxndrJ kuratiert, geprüft und veröffentlicht.*\n"
        )
    if "Haftung" not in body[-300:]:
        body += (
            "\n*Haftungsausschluss: Wir übernehmen keine Haftung für den "
            "Inhalt externer Links. Alle Links führen zu Seiten Dritter; "
            "deren Verfügbarkeit und Richtigkeit können sich ohne "
            "Vorankündigung ändern.*\n"
        )

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(fm) + "\n" + body)
    return filename
