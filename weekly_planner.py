# weekly_planner.py – Erzeugt den 7-Tage-Wochenplan (läuft jeden Sonntag).
#
#   python weekly_planner.py                # Plan generieren + speichern
#   python weekly_planner.py --dry-run      # Nur anzeigen, nicht speichern
#   python weekly_planner.py --site-repo /path/site   # Post-Historie einlesen
#
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic

from config import (
    TOPIC_MODEL,
    WEEKLY_PLAN_FILE,
    WEEKLY_PLAN_SYSTEM,
    WEEKLY_PLAN_BRIEF,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _recent_posts(site_repo: str, limit: int = 14) -> list[str]:
    """Liest die letzten N Post-Titel aus dem Site-Repo (_posts/)."""
    posts_dir = Path(site_repo) / "_posts"
    if not posts_dir.is_dir():
        # Fallback: lokales _posts
        posts_dir = Path("_posts")
    if not posts_dir.is_dir():
        return []

    files = sorted(posts_dir.glob("*.md"), reverse=True)
    titles: list[str] = []
    for f in files[:limit]:
        try:
            text = f.read_text(encoding="utf-8")
            # Titel aus Front-Matter
            if "title:" in text:
                for line in text.splitlines():
                    if line.strip().startswith("title:"):
                        t = line.split(":", 1)[1].strip().strip('"').strip("'")
                        if t:
                            titles.append(t)
                        break
            elif text.startswith("# "):
                titles.append(text.splitlines()[0][2:].strip())
            else:
                titles.append(f.stem.replace("-", " ").title())
        except Exception:
            continue
    return titles


def _season_label(dt: datetime) -> str:
    m = dt.month
    if m in (12, 1, 2):
        return "Winter (Nordhalbkugel) / Sommer (Südhalbkugel)"
    if m in (3, 4, 5):
        return "Frühling (Nordhalbkugel) / Herbst (Südhalbkugel)"
    if m in (6, 7, 8):
        return "Sommer (Nordhalbkugel) / Winter (Südhalbkugel)"
    return "Herbst (Nordhalbkugel) / Frühling (Südhalbkugel)"


def _week_label(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _extract_json(raw: str) -> list[dict]:
    """Zieht ein JSON-Array aus der LLM-Antwort (tolerant gegenüber Code-Blöcken)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # Falls der Text mit einer Erklärungszeile beginnt
    if not raw.startswith("["):
        idx = raw.find("[")
        if idx == -1:
            raise ValueError(f"Kein JSON-Array in der Antwort gefunden:\n{raw[:200]}")
        raw = raw[idx:]
    return json.loads(raw)


# ── Kern ─────────────────────────────────────────────────────────────────────

def generate_plan(site_repo: str = "") -> dict:
    """Ruft die LLM ab und gibt den Wochenplan als Dict zurück."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    today = datetime.now()
    recent = _recent_posts(site_repo) if site_repo else []

    recent_text = "\n".join(f"- {t}" for t in recent) if recent else "(keine lokalen Posts gefunden)"

    brief = WEEKLY_PLAN_BRIEF.format(
        week_label=_week_label(today),
        recent_posts=recent_text,
        season=_season_label(today),
        today=today.strftime("%d.%m.%Y"),
    )

    print("      → LLM-Call läuft …")
            kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

    raw = "".join(b.text for b in response.content if b.type == "text").strip()
    slots = _extract_json(raw)

    # Validierung: 7 Slots, alle mit topic
    if len(slots) != 7:
        print(f"      ⚠ Erwartet 7 Slots, bekommen {len(slots)}", file=sys.stderr)
    for i, s in enumerate(slots, 1):
        if not s.get("topic"):
            raise ValueError(f"Slot {i} hat kein 'topic'")
        s.setdefault("day", i)
        s.setdefault("weekday", ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
                                 "Freitag", "Samstag", "Sonntag"][i - 1])
        s.setdefault("category", "Reise")
        s.setdefault("angle", "")
        s.setdefault("hook", "")
        s.setdefault("forbidden", [])
        s.setdefault("feeling", "")
        s.setdefault("image_query", "")

    return {
        "week": _week_label(today),
        "generated_at": today.isoformat(timespec="seconds"),
        "slots": slots,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Wochenplan für 7 Blog-Posts generieren")
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur anzeigen, NICHT speichern")
    ap.add_argument("--site-repo", default=os.getenv("BLOG_SITE_REPO", ""),
                    help="Pfad zum Site-Repo (für Post-Historie)")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("FEHLER: ANTHROPIC_API_KEY ist nicht gesetzt.", file=sys.stderr)
        return 2

    print(f"\n📅 Wochenplan wird generiert …")
    print(f"   Site-Repo: {args.site_repo or '(nicht gesetzt – keine Post-Historie)'}\n")

    try:
        plan = generate_plan(args.site_repo)
    except Exception as e:
        print(f"\n❌ Plan-Generierung fehlgeschlagen: {e}", file=sys.stderr)
        return 1

    # Anzeigen
    print(f"\n{'=' * 62}")
    print(f"  Woche {plan['week']}  ·  {len(plan['slots'])} Slots  ·  {plan['generated_at']}")
    print(f"{'=' * 62}\n")

    for slot in plan["slots"]:
        wd = slot.get("weekday", f"Tag {slot.get('day', '?')}")
        cat = slot.get("category", "?")
        topic = slot.get("topic", "?")
        hook = slot.get("hook", "")
        feeling = slot.get("feeling", "")
        print(f"  {wd:12s}  [{cat}]")
        print(f"  {'':12s}  {topic}")
        if hook:
            print(f"  {'':12s}  Hook: {hook}")
        if feeling:
            print(f"  {'':12s}  Gefühl: {feeling}")
        print()

    if args.dry_run:
        print("=== DRY RUN – Plan NICHT gespeichert ===\n")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    # Speichern
    out = Path(WEEKLY_PLAN_FILE)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ Wochenplan gespeichert: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
