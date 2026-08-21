# blog_automate v2

KI-gestützte Blog-Pipeline für **blog.pandango.de** – mit Recherche, Lektorat
und Transparenz statt „random Land × random Thema".

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
publisher.py          Markdown + Frontmatter (author, ai_assisted: true, sources)
orchestrator.py       CLI, die alles sequenziert + run_log.jsonl
```

## Schnellstart (lokal)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-…

# Nur Thema + Recherche prüfen
python orchestrator.py --dry-run

# Freies Thema
python orchestrator.py --topic "Markttag in Leipzig" --context "Fokus: Gemüsestand"

# Kompletten Beitrag erzeugen (landet in _posts/)
python orchestrator.py
```

## GitHub-Actions

`.github/workflows/generate-blog-post.yml` läuft Mo/Do/So um 08:00 Berlin.

Zwei Modi (Repo-Variable `PR_FLOW`):

| `PR_FLOW` | Verhalten |
|---|---|
| `true` (empfohlen) | Erzeugt einen **Pull Request**, du mergest nach Review |
| `false` | Push direkt nach `main` (wie bisher) |

Erforderliches Secret: `ANTHROPIC_API_KEY`.

## Qualitäts-Maßnahmen vs. v1

- **Recherche vor dem Schreiben** – Namen/Fakten müssen belegt sein (Editor
  streicht alles, was nicht in den Quellen steht → keine „Sofia Jern" mehr).
- **Kuratierte Themen** statt Zufallsgenerator – keine „Exportprodukte
  Antarktis"-Kombos.
- **Stimm-Regeln + verbotene Floskeln** sind im Prompt, der Lektor prüft sie.
- **Variable Länge** (450–1100 Wörter) & freie Struktur.
- **Quellen-Sektion** in jedem Beitrag + `sources:` im Frontmatter.
- **Transparenz**: `author: lxndrJ`, `ai_assisted: true`, Hinweis am Ende.
- **Dreimal pro Woche** statt täglich – Konstanz schlägt Häufigkeit.
- **Review per PR** optional – menschlicher Merge-Stempel.

## Modelle (per Env überschreibbar)

| Rolle | Default |
|---|---|
| Recherche | `claude-haiku-4-5` |
| Entwurf | `claude-haiku-4-5` |
| Lektor | `claude-haiku-4-5` (besser: `claude-sonnet-4-5`) |

## Altes (noch vorhanden)

`generate_blog_post.py`, `anthropic_config.py`, `countries.db`, `themes.db`,
`unsplash_image.py`, `auto_push_blog.sh` bleiben für Abwärtskompatibilität –
die neue Pipeline nutzt sie nicht.
