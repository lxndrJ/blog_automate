# AGENTS.md

German-language blog automation pipeline. One post per day: research → draft →
edit, then push to a **second** repository. The repo you are in only *generates*;
the site repo `lxndrJ/blog.pandango.de` is the **only** source of published posts
(`_posts/`). Published copies live in `archive/` here as evidence only — do not
edit posts here expecting them to appear live.

## Commands (local)

```bash
pip install -r requirements.txt                 # Python 3.12

python orchestrator.py                          # 1 post, curated topic, no push
python orchestrator.py --dry-run                # topic + research only, no text/push
python orchestrator.py --topic "..." [--context "..."] [--category Reise]
python orchestrator.py --keep                   # show final markdown, don't write to _posts/
python orchestrator.py --daily                  # 3 posts (Reise, Kochen/Essen, Work-Life Balance)
python orchestrator.py --force                  # bypass title-duplicate block
python orchestrator.py --site-repo /path        # push to site repo + archive here

python daily_publisher.py [--day 1-7] [--dry-run] [--force]   # publish today's plan slot
python weekly_planner.py [--dry-run]                            # write weekly_plan.json
python titles.py --check "TITLE" | --list | --count            # inspect title log
```

There is **no test suite, no lint, no typecheck, and no task runner**. The only
verification is running `orchestrator.py --dry-run` (needs a working provider).
At least one provider must be available or every entrypoint exits with code 2.

## Provider wiring (do not bypass)

- Agents call **only** `llm_client.chat(...)` — never `router` or
  `providers/*` directly. `llm_client.py` is the single stable interface.
- `router.py` picks the provider from env `BLOG_LLM_PROVIDER`:
  - `auto` (default): `gemini → anthropic → mistral → ollama`, first *available*
    wins; a broken provider is skipped, not fatal.
  - pinned (`gemini`/`anthropic`/`mistral`/`ollama`): that provider only, hard
    error if unavailable (no silent fallback).
- Availability per provider: Gemini → `GEMINI_API_KEY` (plain REST via
  `requests`, **no SDK**); Anthropic → `ANTHROPIC_API_KEY` + SDK; Mistral →
  `MISTRAL_API_KEY` + `mistralai`; Ollama → running server
  (`OLLAMA_BASE_URL`, default `http://localhost:11434`).
- One model per provider, each overridable by env: `BLOG_GEMINI_MODEL`,
  `BLOG_RESEARCH_MODEL`, `BLOG_MISTRAL_MODEL`, `BLOG_OLLAMA_MODEL`.

## Web search (model-independent)

`websearch.py` does the research — agents never use an LLM server-side search
tool. Cascade, first non-empty wins:

1. Google CSE (`GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX`, ~100 free/day)
2. Brave (`BRAVE_API_KEY`)
3. DuckDuckGo HTML — keyless, works locally, **usually blocked from cloud IPs**
4. Wikipedia API — keyless, reliable in CI

Consequence: in GitHub Actions without CSE/Brave keys, search silently degrades
to Wikipedia. If CI research looks thin, that is why.

## Title dedup (hard block) + time-anchor guard

- `titles.json` logs every used title. `orchestrator` **aborts** (rc=1) on a
  duplicate title unless `--force`. Drafts are seeded with the last 50 titles so
  collisions are rare by design. Normalize before comparing: case-insensitive,
  umlauts stripped, `&`→`und`.
- Known LLM bias: topics anchored to a **specific clock time**
  ("9:07-Pause", "um 16:00 Uhr"). `topic_generator._is_time_anchored()` rejects
  these (retries with an explicit ban, then raises). This guard runs in
  `daily_publisher`, `weekly_planner`, and the `config.py` voice rules. Don't
  "fix" a time-anchored title by loosening the guard — pick a new topic.

## State files (tracked, CI pushes them — treat as shared data)

`weekly_plan.json` (7-day plan), `titles.json`, `run_log.jsonl` (append-only),
`history.json`, and `archive/` (published posts). `.env` is gitignored and is
loaded by `image.py` (`load_dotenv()` from CWD). Post timestamps are the real
generation time in `Europe/Berlin` (not a fixed clock time).

## CI (`.github/workflows/`)

- `daily_publish.yml` — cron `0 5 * * *` (05:00 UTC). Checks out **both** repos
  (site via `BLOG_SYNC_TOKEN` PAT into `site/`), runs `daily_publisher.py`,
  pushes site `_posts/`, then pushes pipeline `archive/`+logs.
- `weekly_plan.yml` — cron `0 4 * * mon`. ⚠️ The workflow name and comment say
  "Sonntag" (Sunday) but the cron actually fires **Monday** 04:00 UTC. Trust the
  cron over the name if you reason about timing.
- `manual_post.yml` — `workflow_dispatch`, single post via `orchestrator.py`.
- `gitleaks.yml` — secret scan on push/PR.
- All CI jobs pin `BLOG_LLM_PROVIDER: gemini` and read the model from the
  **repository variable** `GEMINI_MODEL` (`Settings → Secrets and variables →
  Actions → Variables`), not from `config.py`.

## Gotchas

- The README is partially **stale**: it references
  `.github/workflows/generate-blog-post.yml` (does not exist — the real one is
  `daily_publish.yml`) and a "Altes (v1)" file set that has been **deleted**.
  Trust the code and the workflow files, not those README lines.
- No `_posts/` directory in this repo by default; posts land in the site repo's
  `_posts/` (or `BLOG_POSTS_DIR` / `POSTS_DIR`). `publisher.save()` writes
  markdown + honest frontmatter (`ai_assisted: true`, `author: lxndrJ`,
  `sources:`).
- Images (`image.py`, `publisher._find_image`) fall back
  Unsplash → Pexels → Wikimedia Commons and are **never fatal** — a post ships
  without an image rather than failing.
