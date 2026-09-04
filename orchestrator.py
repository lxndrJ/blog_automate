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

import topics
import publisher
import titles
import router
import topic_generator
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
    # git diff --cached --quiet: Exit 0 = keine Änderungen, Exit 1 = Änderungen vorhanden
    # → beides ist ein normaler Zustand, nicht ein Fehler
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=site_repo, capture_output=True, text=True)
    if diff.returncode != 0:
        _git(site_repo, "commit", "-m", f"Blog-Post: {title}")
        _git(site_repo, "push", "origin", "HEAD")
        print("      ✔ In blog.pandango.de gepusht")
    else:
        print("      → Site-Repo ohne Änderungen, Push übersprungen")

    # 3) Im Pipeline-Repo archivieren → keine doppelte Verwaltung
    archived = arch.archive_post(filename)
    _git(".", "config", "user.name", BOT_NAME)
    _git(".", "config", "user.email", BOT_EMAIL)
    _git(".", "add", "-A", "_posts", "archive", "titles.json")
    diff2 = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=".", capture_output=True, text=True)
    if diff2.returncode != 0:
        _git(".", "commit", "-m", f"Archive: {post_name} (veröffentlicht auf blog.pandango.de)")
    print(f"      ✔ Im Pipeline-Repo archiviert: {archived}")
    return archived


# ── Main ───────────────────────────────────────────────────────────────────

def _generate_single(topic: str, context: str, category: str, image: str | None,
                     args, image_query: str = "") -> int:
    """Generiert EINEN Post durch die komplette Pipeline.

    Returns:
        0 auf Erfolg, 1 bei Titel-Kollision (abgebrochen), 2 bei Fehler.
    """
    print(f"\n{'='*60}")
    print(f"  Kategorie: {category}")
    print(f"  Thema:     {topic}")
    if image_query:
        print(f"  Bild-Query: {image_query}")
    print(f"{'='*60}\n")

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

    # 2) Entwurf (mit letzten 50 Titeln als Kontext → vermeidet Duplikate)
    print("[2/3] Entwurf läuft …")
    recent_titles = titles.all_titles()[-50:]
    draft = drafter.run(topic, context, res["research"], res["sources"], recent_titles)
    print(f"      → {len(draft.split())} Wörter\n")

    # 3) Lektorat
    print("[3/3] Lektorat läuft …")
    final, notes = editor.run(draft, res["research"], res["sources"])
    for n in notes:
        print("      •", n)

    # Arbeitstitel aus dem ersten Markdown-Heading, sonst Kurztitel
    title = _title_from(final) or topic
    print(f"\n## Titel: {title}\n")

    # ── Titel-Duplikat-Check (HARTE Blockade) ──
    if titles.is_duplicate(title):
        if args.force:
            print(f"⚠ TITEL-SCHLAG (forced): '{title}' wurde bereits verwendet, aber --force gesetzt.")
        else:
            print(f"\n❌ ABGEBROCHEN: '{title}' wurde bereits verwendet!")
            similar = titles.find_similar(title, threshold=50)
            for s in similar[:5]:
                print(f"    {s['similarity']}% – {s['title']} ({s.get('date', '?')})")
            print("\n→ Bitte neuen Titel verwenden oder --force übergeben.")
            return 1
    else:
        similar = titles.find_similar(title, threshold=80)
        if similar:
            print(f"⚠ Ähnliche Titel gefunden:")
            for s in similar[:3]:
                print(f"    {s['similarity']}% – {s['title']} ({s.get('date', '?')})")
        print(f"  ✔ Titel ist neu ({titles.count() + 1}. Titel gesamt)")

    if args.keep:
        print(final)
        return 0

    filename = publisher.save(title, final, image, res["sources"], category=category,
                             image_query=image_query)
    print(f"✔ Gespeichert: {filename}")

    # Titel im Log registrieren
    from datetime import datetime
    titles.register(title, datetime.now().strftime("%Y-%m-%d"), filename)

    topics.record(topic, f"[{category}] {topic}", filename, res["sources"])
    log_run({
        "topic": topic,
        "category": category,
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


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Blog-Beitrag generieren (Recherche → Entwurf → Lektorat)"
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur Thema + Recherche, kein Text, kein Push")
    ap.add_argument("--daily", action="store_true",
                    help="Täglicher Modus: 3 Posts (Reise, Kochen/Essen, Work-Life Balance)")
    ap.add_argument("--topic",
                    help="Freies Thema (überspringt Kuratierte Auswahl)")
    ap.add_argument("--category", default="Reise",
                    help="Kategorie für den Post (Default: Reise)")
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
    ap.add_argument("--force", action="store_true",
                    help="Titel-Duplikate ignorieren und trotzdem speichern")
    args = ap.parse_args()

    if args.site_repo:
        os.environ["BLOG_SITE_REPO"] = args.site_repo

    if not router.available_providers():
        print("FEHLER: Kein LLM-Provider verfügbar. Setze ANTHROPIC_API_KEY "
              "oder MISTRAL_API_KEY, oder starte Ollama (BLOG_LLM_PROVIDER=ollama).",
              file=sys.stderr)
        return 2

    # ── DAILY MODUS: 3 Posts (Reise, Kochen/Essen, Work-Life Balance) ──
    if args.daily:
        print("📅 DAILY MODUS – 3 Posts werden generiert\n")
        recent = titles.all_titles()[-50:]
        day_set = topic_generator.generate_daily_set(recent)

        failures = 0
        for item in day_set:
            topic = item["topic"]
            context = item["context"]
            category = item["category"]
            img_q = item.get("image_query", "")
            rc = _generate_single(topic, context, category, args.image, args,
                                 image_query=img_q)
            if rc != 0:
                failures += 1
                print(f"\n⚠ Post [{category}] fehlgeschlagen (rc={rc}), nächster wird versucht.\n")

        # Nach allen Posts: Site-Repo push + Pipeline-Repo archivieren
        if args.site_repo and failures < 3:
            print("\n📦 Site-Repo push …")
            # _publish_to_site wird in _generate_single aufgerufen,
            # aber wir sichern hier nochmal alle Änderungen
            site_repo = os.environ.get("BLOG_SITE_REPO", "")
            if site_repo and os.path.isdir(os.path.join(site_repo, ".git")):
                _git(site_repo, "config", "user.name", BOT_NAME)
                _git(site_repo, "config", "user.email", BOT_EMAIL)
                _git(site_repo, "add", "_posts")
                diff = subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    cwd=site_repo, capture_output=True, text=True
                )
                if diff.returncode != 0:
                    _git(site_repo, "commit", "-m", f"Blog: 3 Posts $(date +%F)")
                    _git(site_repo, "push", "origin", "HEAD")
                    print("      ✔ Site-Repo gepusht")
                else:
                    print("      → Site-Repo ohne neue Änderungen")

        print(f"\n{'='*60}")
        print(f"  FERTIG: {3 - failures}/3 Posts erfolgreich")
        print(f"{'='*60}")
        return 0 if failures == 0 else 1

    # ── SINGLE-POST MODUS (bestehendes Verhalten) ──
    category = args.category

    # 0) Thema wählen
    if args.topic:
        topic, context = args.topic, args.context
        img_q = ""
    else:
        # AI-Themengenerator (neu) mit Fallback auf Templates
        recent = titles.all_titles()[-50:]
        picked = topic_generator.generate(category, recent)
        topic, context = picked["topic"], picked["context"]
        img_q = picked.get("image_query", "")
        if args.context:
            context += " " + args.context

    print(f"## Thema: {topic}\n")

    rc = _generate_single(topic, context, category, args.image, args, image_query=img_q)

    if rc == 0 and not args.site_repo:
        print("\nNächster Schritt: `--site-repo` übergeben (Workflow macht das automatisch) "
              "oder manuell ins Site-Repo kopieren.")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
