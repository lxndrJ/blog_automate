# agents/drafter.py
# Agent 2: Entwurf – schreibt den Blogtext auf Basis der Recherche.
import random

import anthropic
import os

from config import DRAFTER_MODEL, DRAFTER_SYSTEM, DRAFTER_BRIEF, MAX_TOKENS, LENGTH_HINT


def run(topic: str, context: str, research: str, sources: list[str],
       recent_titles: list[str] | None = None) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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

    response = client.messages.create(
        model=DRAFTER_MODEL,
        max_tokens=MAX_TOKENS,
        system=DRAFTER_SYSTEM,
        messages=[{"role": "user", "content": brief}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text
