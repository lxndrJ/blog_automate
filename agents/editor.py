# agents/editor.py
# Agent 3: Lektor – Fakten-Check, Klischee-Filter, Stimm-Nachschärfung.
import re

import llm_client

from config import EDITOR_MODEL, EDITOR_SYSTEM, EDITOR_BRIEF, MAX_TOKENS


def run(draft: str, research: str, sources: list[str]) -> tuple[str, list[str]]:
    """Gibt (finaler_markdown, edit_notes) zurück.

    Bei Fehlern im Format wird der Entwurf unverändert zurückgegeben.
    """
    brief = EDITOR_BRIEF.format(
        draft=draft,
        research=research,
        sources="\n".join(f"- {s}" for s in sources),
    )

    text, _ = llm_client.chat(
        model=EDITOR_MODEL,
        system=EDITOR_SYSTEM,
        messages=[{"role": "user", "content": brief}],
        max_tokens=MAX_TOKENS,
    )

    final, notes = _parse(text, fallback=draft)
    return final, notes


def _parse(text: str, fallback: str) -> tuple[str, list[str]]:
    m = re.search(
        r"===\s*EDIT NOTES\s*===\s*(.*?)\s*===\s*REVISED MARKDOWN\s*===\s*(.*)",
        text,
        flags=re.S,
    )
    if not m:
        return fallback, ["Editor: erwartetes Format nicht gefunden – Entwurf unverändert übernommen"]

    notes_raw, revised = m.group(1), m.group(2).strip()
    if len(revised) < 200:
        return fallback, ["Editor: überarbeiteter Text zu kurz – Entwurf unverändert übernommen"]

    notes = [ln.strip("- ").strip() for ln in notes_raw.splitlines() if ln.strip().startswith(("-", "*"))]
    return revised, notes or ["(keine Hinweise)"]
