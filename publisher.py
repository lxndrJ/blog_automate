# publisher.py – Markdown + ehrliches Frontmatter schreiben
import os
import re
import sys
from datetime import datetime

from config import POSTS_DIR


def _find_image(topic: str) -> dict | None:
    """Automatische Bildsuche (Wikimedia/Unsplash) – nie fatal, nur Fallback."""
    try:
        from image import pick_image
        r = pick_image(topic)
        return r if r.get("url") else None
    except Exception as e:
        print(f"      (Bildsuche fehlgeschlagen: {e})", file=sys.stderr)
        return None


def _safe_filename(title: str) -> str:
    t = title.lower().replace("&", "und")
    t = re.sub(r"[^a-z0-9äöüß \-]+", "", t)
    return re.sub(r"[\s]+", "-", t).strip("-")[:80]


def save(title: str, content: str, image_url: str | None, sources: list[str]) -> str:
    os.makedirs(POSTS_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{POSTS_DIR}/{date_str}-{_safe_filename(title)}.md"

    # Bild: übergebenes zuerst, sonst automatisch suchen (alle Posts sollen ein Bild haben)
    if not image_url:
        print("      → Bild automatisch gesucht …")
        img = _find_image(title)
        if img:
            image_url = img["url"]
            print(f"      → Bild: {img['source']} ({img['license']})")

    fm = [
        "---",
        "layout: post",
        f'title: "{title}"',
        f"date: {date_str}",
        "author: lxndrJ",
        "ai_assisted: true",
    ]
    if image_url:
        fm.append(f"image: {image_url}")
    if sources:
        fm.append("sources:")
        fm.extend(f"  - {s}" for s in sources)
    fm.append("---")

    body = "\n".join(["", f"![{title}]({image_url})"] if image_url else [""])
    body += "\n" + content.strip() + "\n"

    # Quellen-Sektion sicherstellen (Editor soll sie anlegen; Fallback)
    if sources and "## Quellen" not in content:
        body += "\n## Quellen\n\n" + "\n".join(f"- <{s}>" for s in sources) + "\n"

    # Transparenz-Hinweis ans Ende, falls nicht vorhanden
    if "KI" not in body[-200:]:
        body += (
            "\n---\n\n*Dieser Beitrag wurde KI-gestützt geschrieben "
            "und von lxndrJ kuratiert, geprüft und veröffentlicht.*\n"
        )

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(fm) + "\n" + body)
    return filename
