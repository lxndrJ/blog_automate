# blog_automate

KI-gestützte Blog-Pipeline für **blog.pandango.de** – mit Recherche, Lektorat
und Transparenz.

## Architektur

```
topics.py            Kuratierte Themen-Hooks + Duplikat-Prüfung (history.json)
      │
      ▼
agents/researcher.py  Web-Search (Anthropic Tool) → belegte Fakten + Quellen
      │
      ▼
agents/drafter.py     Stimm-Prompt, 450–1100 Wörter, variable Struktur
      │
      ▼
agents/editor.py      Lektor: Fakten-Check, Klischee-Filter, Quellen-Sektion
      │
      ▼
publisher.py          Markdown + Frontmatter (eindeutiger Timestamp, Berlin-Zone)
      │
      ▼
orchestrator.py       CLI – sequenziert alles, push → Site-Repo, archiviert → archive/
```

## Datenfluss

```
1. Post wird in _posts/ erzeugt (einmalig, mit eindeutigem Timestamp)
2. Post wird nach blog.pandango.de/_posts/ kopiert + gepusht
3. Post wird aus _posts/ in archive/ verschoben (nur Nachweis, keine doppelte Pflege)
```

Das **Site-Repo (blog.pandango.de)** ist die einzige Quelle für veröffentlichte Posts.
Im Pipeline-Repo liegt der Post nur noch in `archive/` als Backup/Nachweis.

## Schnellstart (lokal)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-…

# Nur Thema + Recherche prüfen
python orchestrator.py --dry-run

# Freies Thema
python orchestrator.py --topic "Markttag in Leipzig" --context "Fokus: Gemüsestand"

# Kompletten Beitrag erzeugen (landet in _posts/, kein Push)
python orchestrator.py

# Kompletten Beitrag + Push ins Site-Repo + Archivierung
python orchestrator.py --site-repo /pfad/zu/blog.pandango.de
```

## GitHub Actions

`.github/workflows/generate-blog-post.yml` läuft täglich um 08:00 Berlin.

**Erforderliche Secrets:**
| Secret | Zweck |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API für die 3 Agents |
| `BLOG_SYNC_TOKEN` | GitHub-Personal-Access-Token mit `contents:write` auf `blog.pandango.de` |

## Timestamps

Jeder Post erhält den **tatsächlichen Erzeugungszeitpunkt** in der Zone
`Europe/Berlin` (inkl. Sommerzeit) als Frontmatter-`date`. Das garantiert:

- **Eindeutige Timestamps** – auch bei mehreren Posts am selben Tag
- **Sauberer RSS-Feed** – korrekt sortierbar
- **Keine Kollisionen** – kein fixiertes 08:00 für alle Posts

## Qualitäts-Maßnahmen

- **Recherche vor dem Schreiben** – Namen/Fakten müssen belegt sein
- **Kuratierte Themen** statt Zufallsgenerator
- **Stimm-Regeln + verbotene Floskeln** im Prompt, Lektor prüft sie
- **Variable Länge** (450–1100 Wörter) & freie Struktur
- **Quellen-Sektion** in jedem Beitrag + `sources:` im Frontmatter
- **Transparenz**: `author: lxndrJ`, `ai_assisted: true`, Hinweis am Ende

## Modelle (per Env überschreibbar)

| Rolle | Default | Env |
|---|---|---|
| Recherche | `claude-haiku-4-5` | `BLOG_RESEARCH_MODEL` |
| Entwurf | `claude-haiku-4-5` | `BLOG_DRAFTER_MODEL` |
| Lektor | `claude-haiku-4-5` | `BLOG_EDITOR_MODEL` |

## Altes (v1, noch vorhanden)

`generate_blog_post.py`, `anthropic_config.py`, `countries.db`, `themes.db`,
`unsplash_image.py`, `auto_push_blog.sh`, `markdown_writer.py`, `add_images.py`
bleiben für Abwärtskompatibilität – die aktuelle Pipeline nutzt sie nicht.
