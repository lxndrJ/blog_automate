# agents/drafter.py
# Agent 2: Entwurf – schreibt den Blogtext auf Basis der Recherche.
import random

import anthropic
import os

from config import DRAFTER_MODEL, DRAFTER_SYSTEM, DRAFTER_BRIEF, TEMPERATURE, MAX_TOKENS, LENGTH_HINT


def run(topic: str, context: str, research: str, sources: list[str]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Bewusste Variabilität: 450–1100 Wörter
    words = random.randint(450, 1100)
    length_hint = LENGTH_HINT.format(words=words)

    brief = DRAFTER_BRIEF.format(
        topic=topic,
        research=research or "(keine Recherche verfügbar – nur allgemein schreiben)",
        sources="\n".join(f"- {s}" for s in sources) or "(keine Quellen)",
        context=context,
        length_hint=length_hint,
    )

    response = client.messages.create(
        model=DRAFTER_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=DRAFTER_SYSTEM,
        messages=[{"role": "user", "content": brief}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text
