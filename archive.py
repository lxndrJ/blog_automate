# archive.py – Veröffentlichte Posts aus _posts/ in archive/ verschieben.
#
# Das Site-Repo (blog.pandango.de) ist ab jetzt die EINZIGE Quelle für
# veröffentlichte Posts. Damit müssen wir sie hier nicht doppelt pflegen:
# nach dem Push ins Site-Repo wandert der Post in archive/ und wird dort
# nur noch als Nachweis/Backup aufbewahrt (nicht mehr weiter bearbeitet).
import os
import shutil

POSTS_DIR = os.getenv("BLOG_POSTS_DIR", "_posts")
ARCHIVE_DIR = os.getenv("BLOG_ARCHIVE_DIR", "archive")


def archive_post(post_path: str) -> str:
    """Verschiebt einen Post aus _posts/ nach archive/ und gibt den
    neuen Pfad zurück. Idempotent: existiert die Datei schon im Archiv,
    wird sie dort belassen und nur das Original entfernt.
    """
    post_path = os.path.abspath(post_path)
    if not os.path.isfile(post_path):
        raise FileNotFoundError(f"Post nicht gefunden: {post_path}")

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    dest = os.path.join(ARCHIVE_DIR, os.path.basename(post_path))

    if os.path.abspath(dest) == post_path:
        return dest  # bereits im Archiv

    if os.path.exists(dest):
        print(f"      → Archiv-Eintrag existiert bereits, Original wird gelöscht: {dest}")
        os.remove(post_path)
        return dest

    shutil.move(post_path, dest)
    return dest


def archive_all() -> list[str]:
    """Alle verbleibenden Posts aus _posts/ archivieren."""
    if not os.path.isdir(POSTS_DIR):
        return []
    moved = []
    for name in sorted(os.listdir(POSTS_DIR)):
        if name.lower().endswith((".md", ".markdown")):
            moved.append(archive_post(os.path.join(POSTS_DIR, name)))
    return moved


if __name__ == "__main__":
    if len(os.argv) > 1:
        for p in os.argv[1:]:
            print("Archiviert:", archive_post(p))
    else:
        for p in archive_all():
            print("Archiviert:", p)
