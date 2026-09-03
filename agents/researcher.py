# agents/researcher.py
# Agent 1: Recherche – holt per Web-Search belegte Fakten & Quellen.
# Output: {"research": str, "sources": [str]}
import llm_client

from config import RESEARCH_MODEL, RESEARCH_SYSTEM, RESEARCH_BRIEF, MAX_TOKENS


def run(topic: str, context: str) -> dict:
    brief = RESEARCH_BRIEF.format(topic=topic, context=context)

    research, sources = llm_client.chat(
        model=RESEARCH_MODEL,
        system=RESEARCH_SYSTEM,
        messages=[{"role": "user", "content": brief}],
        max_tokens=MAX_TOKENS,
        web_search=True,
    )

    # Fallback: URLs im Freitext, falls der Provider keine Search-Quellen liefert
    if not sources:
        sources = llm_client.extract_urls(research)

    return {"research": research, "sources": sources[:10]}
