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
