# agents/editor.py
# Agent 3: Lektor – Fakten-Check, Klischee-Filter, Stimm-Nachschärfung.
import re

import anthropic
import os

from config import EDITOR_MODEL, EDITOR_SYSTEM, EDITOR_BRIEF, MAX_TOKENS, TEMPERATURE


def run(draft: str, research: str, sources: list[str]) -> tuple[str, list[str]]:
    """Gibt (finaler_markdown, edit_notes) zurück.

    Bei Fehlern im Format wird der Entwurf unverändert zurückgegeben.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    brief = EDITOR_BRIEF.format(
        draft=draft,
        research=research,
        sources="\n".join(f"- {s}" for s in sources),
    )

    response = client.messages.create(
        model=EDITOR_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=EDITOR_SYSTEM,
        messages=[{"role": "user", "content": brief}],
    )

    text = "".join(b.text for b in response.content if b.type == "text")
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
