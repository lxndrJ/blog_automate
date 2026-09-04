# blog_automate

KI-gestützte Blog-Pipeline für **blog.pandango.de** – mit Recherche, Lektorat
und Transparenz.

## Architektur

```
topics.py            Kuratierte Themen-Hooks + Duplikat-Prüfung (history.json)
      │
      ▼
agents/researcher.py  Web-Search (via LLM-Provider) → belegte Fakten + Quellen
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

# Provider wählen (Default: auto = anthropic → mistral → ollama, nächster verfügbarer)
# Mindestens EINEN Provider verfügbar machen:
export ANTHROPIC_API_KEY=sk-ant-…    # Claude (empfohlen, läuft stabil)
# export MISTRAL_API_KEY=***         # Mistral
# bzw. lokal: Ollama starten (kein Key nötig) + export BLOG_LLM_PROVIDER=ollama

# Optional: Provider explizit fixieren
# export BLOG_LLM_PROVIDER=anthropic   # nur Anthropic, kein Fallback

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
| `ANTHROPIC_API_KEY` | Anthropic (Claude) – stabiler Default-Provider |
| `MISTRAL_API_KEY` | Mistral – optional, Fallback/Alternative |
| `BLOG_LLM_PROVIDER` | optional: `auto` (Default) / `anthropic` / `mistral` / `ollama` |
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

## LLM-Provider (Anthropic, Mistral, Ollama – isoliert)

Alle Agents nutzen `llm_client.py` als **einzige, stabile Schnittstelle**
(`llm_client.chat(...)`). Dahinter liegt eine Provider-Abstraktion:

```
llm_client.py            dünne Fassade (chat, extract_urls) – Agents rufen nur hier an
   ▼
router.py                wählt Provider (BLOG_LLM_PROVIDER) + Fallback-Logik
   ├── providers/anthropic_provider.py   stabil, 1:1 der bewährte Claude-Pfad
   ├── providers/mistral_provider.py     Mistral-Quirks isoliert in einer Datei
   └── providers/ollama_provider.py      lokale Modelle (kein Key nötig)
```

**Routing** (Env `BLOG_LLM_PROVIDER`):
- `auto` (Default): `anthropic → mistral → ollama`. Der nächste **verfügbare**
  Provider wird genutzt. Ein defekter Provider (Key fehlt, SDK fehlt, API-Fehler,
  Server down) bricht die anderen **nicht**.
- `anthropic` / `mistral` / `ollama`: nur dieser Provider, sonst klare Fehlermeldung.

**Verfügbarkeit:** Anthropic → `ANTHROPIC_API_KEY` + SDK. Mistral → `MISTRAL_API_KEY`
+ `mistralai`. Ollama → laufender Server (`OLLAMA_BASE_URL`, Default
`http://localhost:11434`).

**Modellnamen:** In `config.py` stehen Claude-Namen. Anthropic nimmt sie 1:1.
Mistral/Ollama übersetzen sie selbst (`resolve_model`) oder nutzen einen Override:
`BLOG_MISTRAL_MODEL`, `BLOG_OLLAMA_MODEL`.

## Modelle (per Env überschreibbar)

| Rolle | Default (Claude) | Env |
|---|---|---|
| Recherche | `claude-haiku-4-5` | `BLOG_RESEARCH_MODEL` |
| Entwurf | `claude-haiku-4-5` | `BLOG_DRAFTER_MODEL` |
| Lektor | `claude-haiku-4-5` | `BLOG_EDITOR_MODEL` |
| Themen | `claude-haiku-4-5` | `BLOG_TOPIC_MODEL` |

Provider-Overrides: `BLOG_MISTRAL_MODEL`, `BLOG_OLLAMA_MODEL`, `OLLAMA_BASE_URL`.

## Altes (v1, noch vorhanden)

`generate_blog_post.py`, `anthropic_config.py`, `countries.db`, `themes.db`,
`unsplash_image.py`, `auto_push_blog.sh`, `markdown_writer.py`, `add_images.py`
bleiben für Abwärtskompatibilität – die aktuelle Pipeline nutzt sie nicht.
