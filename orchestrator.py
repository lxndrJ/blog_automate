# orchestrator.py – CLI, die die drei Agents sequenziert.
#
#   python orchestrator.py                # 1 Beitrag erzeugen
#   python orchestrator.py --dry-run      # nur Thema + Recherche anzeigen
#   python orchestrator.py --topic "…"    # freies Thema statt Kuratiertem
#   python orchestrator.py --keep          # Markdown NICHT nach _posts schreiben
#                                         # (zwecks manuellem Review)
import argparse
import json
import os
import sys
from datetime import datetime

os.environ.setdefault("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))

import topics
import publisher
from agents import researcher, drafter, editor


def log_run(record: dict) -> None:
    with open("run_log.jsonl", "a", encoding="utf-8") as f:
        record["ts"] = datetime.now().isoformat(timespec="seconds")
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Blog-Beitrag generieren (Recherche → Entwurf → Lektorat)")
    ap.add_argument("--dry-run", action="store_true", help="Nur Thema + Recherche, kein Text, kein Push")
    ap.add_argument("--topic", help="Freies Thema (überspringt Kuratierte Auswahl)")
    ap.add_argument("--context", default="", help="Zusätzlicher Kontext zum Thema")
    ap.add_argument("--image", help="Optionale Bild-URL")
    ap.add_argument("--keep", action="store_true", help="Nicht in _posts/ schreiben, nur anzeigen")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("FEHLER: ANTHROPIC_API_KEY ist nicht gesetzt.", file=sys.stderr)
        return 2

    # 0) Thema wählen
    if args.topic:
        topic, context = args.topic, args.context
        base = args.topic
    else:
        picked = topics.pick_topic(topics.used_topics())
        topic, context = picked["topic"], picked["context"]
        if args.context:
            context += " " + args.context

    print(f"## Thema: {topic}\n")

    # 1) Recherche
    print("[1/3] Recherche läuft …")
    res = researcher.run(topic, context)
    print(f"      → {len(res['research'].split())} Wörter, {len(res['sources'])} Quellen\n")

    if args.dry_run:
        print("=== RECHERCHE ===\n")
        print(res["research"])
        print("\n=== QUELLEN ===")
        for s in res["sources"]:
            print(" -", s)
        return 0

    # 2) Entwurf
    print("[2/3] Entwurf läuft …")
    draft = drafter.run(topic, context, res["research"], res["sources"])
    print(f"      → {len(draft.split())} Wörter\n")

    # 3) Lektorat
    print("[3/3] Lektorat läuft …")
    final, notes = editor.run(draft, res["research"], res["sources"])
    for n in notes:
        print("      •", n)

    # Arbeitstitel aus dem ersten Markdown-Heading, sonst Kurztitel
    title = _title_from(final) or topic
    print(f"\n## Titel: {title}\n")

    if args.keep:
        print(final)
        return 0

    filename = publisher.save(title, final, args.image, res["sources"])
    print(f"✔ Gespeichert: {filename}")

    topics.record(topic, base, filename, res["sources"])
    log_run({
        "topic": topic,
        "title": title,
        "file": filename,
        "sources": res["sources"],
        "words": len(final.split()),
        "editor_notes": notes,
    })
    print("\nNächster Schritt: `git add` + PR auf blog.pandango.de (siehe README).")
    return 0


def _title_from(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


if __name__ == "__main__":
    raise SystemExit(main())
