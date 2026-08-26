# titles.py – Titel-Log & Duplikat-Schutz
"""
Hält eine zentrale Liste aller bereits verwendeten Titel.
Wird bei der Generierung abgefragt, um Titel-Kollisionen zu vermeiden.

Datei: titles.json (im selben Verzeichnis)
Format:
[
  {
    "title": "Gebirge und Wanderwege in Vanuatu",
    "slug": "gebirge-und-wanderwege-in-vanuatu",
    "date": "2025-08-22",
    "file": "2025-08-22-gebirge-und-wanderwege-in-vanuatu.md"
  },
  ...
]
"""
import json
import os
import re
import unicodedata
from pathlib import Path

TITLES_FILE = Path(__file__).resolve().parent / "titles.json"


def _normalize(title: str) -> str:
    """Normalisiert einen Titel für den Vergleich (case-insensitive, ohne Umlaute)."""
    t = title.lower().strip()
    # Umlaute → latin1
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # & → und
    t = t.replace("&", "und")
    # nur alphanumerisch + Leerzeichen
    t = re.sub(r"[^a-z0-9äöüß ]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _slug(title: str) -> str:
    """Erzeugt denselben Slug wie publisher._safe_filename()."""
    t = title.lower().replace("&", "und")
    t = re.sub(r"[^a-z0-9äöüß \-]+", "", t)
    return re.sub(r"[\s]+", "-", t).strip("-")[:80]


def load() -> list[dict]:
    """Lädt das Titel-Log. Leere Liste, wenn die Datei fehlt."""
    if not TITLES_FILE.exists():
        return []
    try:
        with open(TITLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save(entries: list[dict]) -> None:
    """Schreibt das Titel-Log."""
    with open(TITLES_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def register(title: str, date: str, filename: str) -> None:
    """Registriert einen neuen Titel im Log (idempotent – keine Duplikate)."""
    entries = load()
    norm = _normalize(title)
    slug = _slug(title)
    # Prüfen ob schon vorhanden (nach normalem Titel oder Slug)
    for e in entries:
        if _normalize(e.get("title", "")) == norm or e.get("slug", "") == slug:
            return  # bereits vorhanden
    entries.append({
        "title": title,
        "slug": slug,
        "date": date,
        "file": os.path.basename(filename) if filename else "",
    })
    save(entries)


def is_duplicate(title: str) -> bool:
    """Prüft ob ein Titel (oder sehr ähnlicher) bereits verwendet wurde."""
    norm = _normalize(title)
    entries = load()
    for e in entries:
        if _normalize(e.get("title", "")) == norm:
            return True
    return False


def find_similar(title: str, threshold: int = 70) -> list[dict]:
    """Findet ähnliche Titel (einfacher Similarity-Score auf normalisierten Strings).

    Nutzt einen einfachen Token-Overlap-Score.
    threshold: 0-100, ab welchem Prozentsatz ein Titel als "ähnlich" gilt.
    """
    norm = _normalize(title)
    tokens = set(norm.split())
    if not tokens:
        return []

    similar = []
    for e in load():
        e_norm = _normalize(e.get("title", ""))
        e_tokens = set(e_norm.split())
        if not e_tokens:
            continue
        # Jaccard-ähnlicher Score
        intersection = tokens & e_tokens
        union = tokens | e_tokens
        score = len(intersection) / len(union) * 100 if union else 0
        if score >= threshold:
            similar.append({**e, "similarity": round(score, 1)})
    return sorted(similar, key=lambda x: x["similarity"], reverse=True)


def all_titles() -> list[str]:
    """Gibt alle registrierten Titel als Liste zurück."""
    return [e.get("title", "") for e in load()]


def count() -> int:
    """Anzahl der registrierten Titel."""
    return len(load())


def build_from_posts(posts_dir: str) -> int:
    """Initialisiert das Titel-Log aus existierenden Post-Dateien.

    Scannt alle .md-Dateien in posts_dir, extrahiert Titel aus dem Front Matter
    und registriert sie. Gibt die Anzahl neu hinzugefügter Titel zurück.
    """
    from pathlib import Path as P
    posts = P(posts_dir)
    if not posts.exists():
        print(f"  ⚠ Posts-Verzeichnis nicht gefunden: {posts_dir}")
        return 0

    entries = load()
    existing_norms = set()
    existing_slugs = set()
    for e in entries:
        existing_norms.add(_normalize(e.get("title", "")))
        existing_slugs.add(e.get("slug", ""))

    added = 0
    for md_file in sorted(posts.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        # Front Matter parsen
        fm_match = re.match(r'\A---\s*\n(.*?)\n---\s*\n?', content, re.DOTALL)
        if not fm_match:
            continue
        fm = fm_match.group(1)

        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        if not title_match:
            continue
        title = title_match.group(1).strip()

        date_match = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', fm, re.MULTILINE)
        date = date_match.group(1) if date_match else ""

        norm = _normalize(title)
        slug = _slug(title)
        if norm in existing_norms or slug in existing_slugs:
            continue

        entries.append({
            "title": title,
            "slug": slug,
            "date": date,
            "file": md_file.name,
        })
        existing_norms.add(norm)
        existing_slugs.add(slug)
        added += 1

    if added:
        save(entries)
        print(f"  ✔ {added} Titel aus Posts importiert (gesamt: {len(entries)})")
    else:
        print(f"  → Kein neuer Titel (Log hat bereits {len(entries)} Einträge)")
    return added


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Titel-Log verwalten")
    ap.add_argument("--build", metavar="POSTS_DIR",
                    help="Initialisiere das Log aus existierenden Posts")
    ap.add_argument("--check", metavar="TITLE",
                    help="Prüfe ob ein Titel bereits verwendet wurde")
    ap.add_argument("--list", action="store_true",
                    help="Zeige alle Titel")
    ap.add_argument("--count", action="store_true",
                    help="Zeige Anzahl")
    args = ap.parse_args()

    if args.build:
        build_from_posts(args.build)
    elif args.check:
        dup = is_duplicate(args.check)
        similar = find_similar(args.check)
        if dup:
            print(f"❌ DUPLIKAT: '{args.check}' wurde bereits verwendet")
        elif similar:
            print(f"⚠ Ähnliche Titel gefunden:")
            for s in similar[:5]:
                print(f"  {s['similarity']}% – {s['title']}")
        else:
            print(f"✅ '{args.check}' ist ein neuer Titel")
    elif args.list:
        for i, t in enumerate(all_titles(), 1):
            print(f"  {i:3d}. {t}")
    elif args.count:
        print(count())
    else:
        print(f"Titel-Log: {count()} Einträge in {TITLES_FILE}")
