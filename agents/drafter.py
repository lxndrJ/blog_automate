# agents/drafter.py
# Agent 2: Entwurf – schreibt den Blogtext auf Basis der Recherche.
import random

import llm_client

from config import DRAFTER_MODEL, DRAFTER_SYSTEM, DRAFTER_BRIEF, MAX_TOKENS, LENGTH_HINT


def run(topic: str, context: str, research: str, sources: list[str],
       recent_titles: list[str] | None = None) -> str:
    # Bewusste Variabilität: 450–1100 Wörter
    words = random.randint(450, 1100)
    length_hint = LENGTH_HINT.format(words=words)

    # Titel-Duplikat-Vermeidung: letzte 50 Titel als Kontext
    title_hint = ""
    if recent_titles:
        title_list = "\n".join(f"- {t}" for t in recent_titles[-50:])
        title_hint = (
            f"\nWICHTIG – Folgende Titel wurden bereits verwendet. "
            f"Wähle einen NEUEN, anderen Titel:\n{title_list}\n"
        )

    brief = DRAFTER_BRIEF.format(
        topic=topic,
        research=research or "(keine Recherche verfügbar – nur allgemein schreiben)",
        sources="\n".join(f"- {s}" for s in sources) or "(keine Quellen)",
        context=context,
        length_hint=length_hint,
    ) + title_hint

    text, _ = llm_client.chat(
        model=DRAFTER_MODEL,
        system=DRAFTER_SYSTEM,
        messages=[{"role": "user", "content": brief}],
        max_tokens=MAX_TOKENS,
    )

    return text.strip()
