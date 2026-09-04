# daily_publisher.py – Veröffentlicht den heutigen Slot aus dem Wochenplan.
#
#   python daily_publisher.py                # Heutigen Slot veröffentlichen
#   python daily_publisher.py --dry-run      # Nur Slot anzeigen, nichts generieren
#   python daily_publisher.py --day 3        # Bestimmten Tag (1-7)
#   python daily_publisher.py --site-repo /path/site
#
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import router

from config import WEEKLY_PLAN_FILE


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_plan() -> dict:
    path = Path(WEEKLY_PLAN_FILE)
    if not path.exists():
        raise FileNotFoundError(
            f"Wochenplan nicht gefunden: {path.resolve()}\n"
            f"→ Zuerst `python weekly_planner.py` ausführen."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def today_slot(plan: dict, day_override: int | None = None) -> dict:
    """Gibt den Slot für den Wochentag zurück (1=Mo … 7=So)."""
    day = day_override or datetime.now().isoweekday()
    for slot in plan["slots"]:
        if slot.get("day") == day:
            return slot
    raise ValueError(f"Kein Slot für Tag {day} in {WEEKLY_PLAN_FILE}")


def mark_published(plan: dict, day: int) -> None:
    for slot in plan["slots"]:
        if slot.get("day") == day:
            slot["published"] = True
            slot["published_at"] = datetime.now().isoformat(timespec="seconds")
            break
    Path(WEEKLY_PLAN_FILE).write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _is_published(slot: dict) -> bool:
    return slot.get("published", False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Heutigen Slot aus dem Wochenplan veröffentlichen"
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur Slot anzeigen, keinen Post generieren")
    ap.add_argument("--day", type=int, choices=range(1, 8),
                    help="Tag 1-7 (Default: heutiger Wochentag)")
    ap.add_argument("--site-repo", default=os.getenv("BLOG_SITE_REPO", ""),
                    help="Pfad zum Site-Repo (blog.pandango.de)")
    ap.add_argument("--force", action="store_true",
                    help="Auch veröffentlichen, wenn Slot bereits als 'published' markiert ist")
    args = ap.parse_args()

    if not router.available_providers():
        print("FEHLER: Kein LLM-Provider verfügbar. Setze ANTHROPIC_API_KEY "
              "oder MISTRAL_API_KEY, oder starte Ollama (BLOG_LLM_PROVIDER=ollama).",
              file=sys.stderr)
        return 2

    # Plan laden
    try:
        plan = load_plan()
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    # Slot finden
    try:
        slot = today_slot(plan, args.day)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    day = slot.get("day", "?")
    weekday = slot.get("weekday", f"Tag {day}")
    category = slot.get("category", "Reise")
    topic = slot.get("topic", "?")
    angle = slot.get("angle", "")
    hook = slot.get("hook", "")
    forbidden = slot.get("forbidden", [])
    feeling = slot.get("feeling", "")
    image_query = slot.get("image_query", "")

    print(f"\n{'=' * 62}")
    print(f"  {weekday}  ·  Woche {plan.get('week', '?')}")
    print(f"{'=' * 62}")
    print(f"  Kategorie:   {category}")
    print(f"  Thema:       {topic}")
    if angle:
        print(f"  Winkel:      {angle}")
    if hook:
        print(f"  Hook:        {hook}")
    if forbidden:
        print(f"  Verboten:    {', '.join(forbidden)}")
    if feeling:
        print(f"  Zielgefühl:  {feeling}")
    if image_query:
        print(f"  Bild-Query:  {image_query}")
    print()

    # Bereits veröffentlicht?
    if _is_published(slot) and not args.force:
        print(f"⚠ Slot {weekday} ist bereits als veröffentlicht markiert "
              f"({slot.get('published_at', '?')}).")
        print("  → --force nutzen, um trotzdem zu veröffentlichen.")
        return 0

    if args.dry_run:
        print("=== DRY RUN – kein Post generiert ===")
        return 0

    # ── Pipeline ausführen (Recherche → Entwurf → Lektorat) ──
    print("[1/3] Pipeline startet: Recherche → Entwurf → Lektorat …\n")

    import orchestrator

    class _Args:
        dry_run = False
        keep = False
        force = False
        site_repo = args.site_repo
        image = None

    a = _Args()
    if args.site_repo:
        os.environ["BLOG_SITE_REPO"] = args.site_repo

    # Kontext aus dem Slot zusammenstellen
    context_parts = []
    if angle:
        context_parts.append(angle)
    if hook:
        context_parts.append(f'Erster Satz (Hook): "{hook}"')
    if forbidden:
        context_parts.append(f"Verbotene Klischees: {', '.join(forbidden)}")
    if feeling:
        context_parts.append(f"Zielgefühl: {feeling}")
    context = "\n".join(context_parts)

    rc = orchestrator._generate_single(
        topic=topic,
        context=context,
        category=category,
        image=None,
        args=a,
        image_query=image_query,
    )

    if rc == 0:
        mark_published(plan, day)
        print(f"\n✔ Slot {weekday} als veröffentlicht markiert.")
    else:
        print(f"\n❌ Pipeline fehlgeschlagen (rc={rc}). Slot NICHT als published markiert.",
              file=sys.stderr)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
