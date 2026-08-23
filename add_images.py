#!/usr/bin/env python3
"""add_images.py – Bestehende Blog-Posts ohne Bild nachträglich bebildern.

Liest _posts/*.md, erkennt Posts ohne `image:`-Frontmatter, sucht per
image.py (Wikimedia Commons → Unsplash) eine Remote-Bild-URL und ergänzt:
  1. `image: <url>` ins Frontmatter (nach der `date:`-Zeile)
  2. `![<title>](<url>)` direkt unter dem Frontmatter

Verwendung:
    python add_images.py [posts_dir]     # Default: ../site/_posts
    python add_images.py --dry-run       # nur anzeigen, nichts schreiben
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from image import pick_image

DRY_RUN = "--dry-run" in sys.argv
POSTS_DIR = Path(sys.argv[sys.argv.index("--dry-run") + 1]) if (
    len(sys.argv) > 2 and not sys.argv[1].startswith("--")) else Path("../site/_posts")

LICENSE_NOTE = {
    "wikimedia": "Bild: Wikimedia Commons",
    "unsplash": "Bild: Unsplash",
}


# Bekannte Länder/Regionen – Fallback wenn der volle Titel zu spezifisch ist
KNOWN_LOCATIONS = [
    "Antarktis", "Jemen", "Sambia", "Niue", "Heard", "Gabun", "Kiribati",
    "Tokelau", "Weissrussland", "Belarus", "Tadschikistan", "Äthiopien",
    "Wallis", "Futuna", "Zentralafrikanische", "Jungferninseln", "Saudi",
    "Mikronesien", "Lettland", "Amerikanische", "Botswana", "Algerien",
    "Kenia", "Niger", "Togo", "Armenien", "Tunesien", "Sudan", "Saint",
    "Barthélemy", "Aruba", "Libanon", "Macao", "Norfolkinsel", "Curaçao",
    "Mayotte", "Vukovar", "Kroatien", "Tschechien", "Tschad", "Fiji",
    "Vanuatu", "Mongolei", "Brasilien", "Kongo", "Georgien", "Trinidad",
    "Tobago", "Elfenbeinküste", "Sint Maarten", "Niederländische Antillen",
    "Seychellen", "Kap Verde", "Komoren", "Marokko", "Tunesien", "Ägypten",
    "Libyen", "Algerien", "Mali", "Niger", "Tschad", "Sudan", "Sambia",
    "Zambia", "Malawi", "Mosambik", "Madagaskar", "Mauritius", "Lesotho",
    "Eswatini", "Simbabwe", "Botswana", "Namibia", "Angola",
    "Französisch", "Polynesien", "Neukaledonien", "Tonga", "Samoa",
    "Fidschi", "Kiribati", "Tuvalu", "Palau", "Marshall",
    "Nauru", "Kiribati", "Cookinseln", "Niue", "Tokelau",
    "Britische", "Amerikanische", "Französische", "Niederländische",
    "Süd-", "Nord-", "Ost-", "West-", "Zentral-",
    "Antarktis", "Arktis", "Polynesien", "Mikronesien", "Melanesien",
]


def extract_location(title: str) -> str | None:
    """Extrahiert einen Ländernamen aus dem Post-Titel als Fallback-Suchbegriff."""
    # Muster: "… in <Land>" (Deutsch: in, auf, bei)
    m = re.search(r'\b(?:in|auf|bei)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)', title)
    if m:
        loc = m.group(1).strip()
        # Entferne generische Wörter
        stop = {"der", "die", "das", "und", "den", "dem", "einer", "einem"}
        words = [w for w in loc.split() if w.lower() not in stop]
        if words:
            return " ".join(words)
    # Fallback: Suche bekannte Ländernamen im Titel
    for loc in KNOWN_LOCATIONS:
        if loc.lower() in title.lower():
            return loc
    return None


def parse_front_matter(text: str) -> tuple[list[str], str]:
    """Trennt Frontmatter (Zeilen) vom Body."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return [], text


def has_image(fm_lines: list[str]) -> bool:
    return any(l.strip().startswith("image:") for l in fm_lines)


def get_title(fm_lines: list[str]) -> str:
    for l in fm_lines:
        if l.strip().startswith("title:"):
            return l.split(":", 1)[1].strip().strip('"')
    return ""


def main() -> int:
    if not POSTS_DIR.is_dir():
        print(f"FEHLER: {POSTS_DIR} existiert nicht", file=sys.stderr)
        return 2

    files = sorted(POSTS_DIR.glob("*.md"))
    todo = []
    for f in files:
        fm, body = parse_front_matter(f.read_text(encoding="utf-8"))
        if not has_image(fm):
            todo.append((f, fm, body, get_title(fm)))

    print(f"{len(todo)} Posts ohne Bild von {len(files)} insgesamt\n")

    ok = fail = 0
    for f, fm, body, title in todo:
        topic = title or f.stem
        print(f"→ {f.name}")
        img = pick_image(topic)

        # Fallback: Land/Region aus dem Titel extrahieren und neu suchen
        if not img or not img.get("url"):
            loc = extract_location(title)
            if loc and loc.lower() != topic.lower():
                print(f"   … Fallback-Suche: \"{loc}\"")
                img = pick_image(loc)

        if not img or not img.get("url"):
            print("   ❌ Kein Bild gefunden – übersprungen")
            fail += 1
            time.sleep(3)  # auch bei Fehlern Pausen halten, damit das Rate-Limit abklingt
            continue

        url = img["url"]
        # 1) Frontmatter: image-Zeile nach date:
        new_fm = []
        inserted = False
        for l in fm:
            new_fm.append(l)
            if not inserted and l.strip().startswith("date:"):
                new_fm.append(f"image: {url}")
                inserted = True
        if not inserted:
            new_fm.append(f"image: {url}")

        # 2) Bild-Embed nach dem Frontmatter
        alt = title or topic
        embed = f"![{alt}]({url})"
        new_body = body
        if f"![" not in new_body[:200]:  # kein Embed bereits vorhanden
            new_body = "\n" + embed + new_body.lstrip("\n")

        out = "---\n" + "\n".join(new_fm) + "\n---" + new_body
        if DRY_RUN:
            print("   ✅ (dry-run) würde schreiben")
        else:
            f.write_text(out, encoding="utf-8")
            print(f"   ✅ {img['source']} – {img['license']}")
        ok += 1
        time.sleep(3)  # Rate-Limit-Schutz (Wikimedia + Unsplash)

    print(f"\nFertig: {ok} bebildert, {fail} ohne Bild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
