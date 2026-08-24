# orchestrator.py – CLI, die die drei Agents sequenziert.
#
#   python orchestrator.py                # 1 Beitrag erzeugen
#   python orchestrator.py --dry-run      # nur Thema + Recherche anzeigen
#   python orchestrator.py --topic "…"    # freies Thema statt Kuratiertem
#   python orchestrator.py --keep         # Markdown NICHT nach _posts schreiben
#   python orchestrator.py --site-repo /path/site
#                                         # Post direkt ins Site-Repo pushen und
#                                         # danach im Pipeline-Repo archivieren
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

os.environ.setdefault("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))

import topics
import publisher
from agents import researcher, drafter, editor

BOT_NAME  = os.getenv("BLOG_BOT_NAME",  "lxndrJ[bot]")
BOT_EMAIL = os.getenv("BLOG_BOT_EMAIL", "actions@github.com")


# ── Helpers ────────────────────────────────────────────────────────────────

def log_run(record: dict) -> None:
    """Appendt einen Lauf-Eintrag zu run_log.jsonl."""
    with open("run_log.jsonl", "a", encoding="utf-8") as f:
        record["ts"] = datetime.now().isoformat(timespec="seconds")
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _git(cwd: str, *cmd: str) -> subprocess.CompletedProcess:
    """git-Aufruf ausführen; bricht die Pipeline ab, wenn er fehlschlägt."""
    result = subprocess.run(["git", *cmd], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"git {' '.join(cmd)} fehlgeschlagen in {cwd}")
    return result


def _title_from(markdown: str) -> str | None:
    """Ersten Markdown-H1 als Titel extrahieren."""
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


# ── Publish + Archive ──────────────────────────────────────────────────────

def _publish_to_site(filename: str, title: str) -> str:
    """Post direkt ins Site-Repo pushen und danach im Pipeline-Repo archivieren.

    Das Site-Repo (blog.pandango.de) ist die EINZIGE Quelle für
    veröffentlichte Posts. Im Pipeline-Repo wandert der Post nach archive/
    (nur Nachweis, keine doppelte Pflege).

    Gibt den Archivpfad zurück.
    """
    import archive as arch

    site_repo = os.environ.get("BLOG_SITE_REPO", "").strip()
    if not site_repo:
        raise RuntimeError("--site-repo / BLOG_SITE_REPO fehlt")
    if not os.path.isdir(os.path.join(site_repo, ".git")):
        raise RuntimeError(f"Site-Repo nicht gefunden (kein .git): {site_repo}")

    filename = os.path.abspath(filename)
    post_name = os.path.basename(filename)

    # 1) Post ins Site-Repo kopieren
    dest = os.path.join(site_repo, "_posts", post_name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        with open(filename, encoding="utf-8") as src, open(dest, encoding="utf-8") as tgt:
            if src.read() == tgt.read():
                print(f"      → Post liegt bereits identisch im Site-Repo: {post_name}")
            else:
                shutil.copy2(filename, dest)
                print(f"      → Post im Site-Repo aktualisiert: {post_name}")
    else:
        shutil.copy2(filename, dest)
        print(f"      → Post im Site-Repo abgelegt: {post_name}")

    # 2) Im Site-Repo committen + pushen (vorher pull, um Konflikte zu vermeiden)
    _git(site_repo, "config", "user.name", BOT_NAME)
    _git(site_repo, "config", "user.email", BOT_EMAIL)
    _git(site_repo, "pull", "--rebase", "--autostash")
    _git(site_repo, "add", "_posts")
    if _git(site_repo, "diff", "--cached", "--quiet").returncode != 0:
        _git(site_repo, "commit", "-m", f"Blog-Post: {title}")
        _git(site_repo, "push", "origin", "HEAD")
        print("      ✔ In blog.pandango.de gepusht")
    else:
        print("      → Site-Repo ohne Änderungen, Push übersprungen")

    # 3) Im Pipeline-Repo archivieren → keine doppelte Verwaltung
    archived = arch.archive_post(filename)
    _git(".", "config", "user.name", BOT_NAME)
    _git(".", "config", "user.email", BOT_EMAIL)
    _git(".", "add", "-A", "_posts", "archive")
    if _git(".", "diff", "--cached", "--quiet").returncode != 0:
        _git(".", "commit", "-m", f"Archive: {post_name} (veröffentlicht auf blog.pandango.de)")
    print(f"      ✔ Im Pipeline-Repo archiviert: {archived}")
    return archived


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Blog-Beitrag generieren (Recherche → Entwurf → Lektorat)"
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur Thema + Recherche, kein Text, kein Push")
    ap.add_argument("--topic",
                    help="Freies Thema (überspringt Kuratierte Auswahl)")
    ap.add_argument("--context", default="",
                    help="Zusätzlicher Kontext zum Thema")
    ap.add_argument("--image",
                    help="Optionale Bild-URL")
    ap.add_argument("--keep", action="store_true",
                    help="Nicht in _posts/ schreiben, nur anzeigen")
    ap.add_argument("--site-repo", default="",
                    help="Pfad zum Site-Repo (blog.pandango.de). Post wird direkt dort "
                         "gepusht und danach im Pipeline-Repo archiviert. "
                         "Alternativ: Env BLOG_SITE_REPO.")
    args = ap.parse_args()

    if args.site_repo:
        os.environ["BLOG_SITE_REPO"] = args.site_repo

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
        base = picked["base"]
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
        "published": bool(args.site_repo),
    })

    if args.site_repo:
        dest = _publish_to_site(filename, title)
        topics.update_file(dest)
        return 0

    print("\nNächster Schritt: `--site-repo` übergeben (Workflow macht das automatisch) "
          "oder manuell ins Site-Repo kopieren.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
