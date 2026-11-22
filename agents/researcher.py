# agents/researcher.py
# Agent 1: Recherche – holt per modellunabhängiger Websuche (websearch.py)
# belegte Fakten & Quellen. Kein serverseitiges Search-Tool des LLM nötig,
# damit funktioniert jeder Provider/ein Modell (auch Gemma).
# Output: {"research": str, "sources": [str]}
import websearch

import llm_client

from config import RESEARCH_MODEL, RESEARCH_SYSTEM, RESEARCH_BRIEF, MAX_TOKENS


def _queries(topic: str, context: str) -> list[str]:
    """Suchanfragen aus Thema + Kontext ableiten (zuerst die besten nennen)."""
    queries = [topic]
    if context and context.strip():
        queries.append(f"{topic} {context.strip()}")
    queries.append(f"{topic} Fakten Geschichte")
    return queries[:3]


def run(topic: str, context: str) -> dict:
    bundle, sources = websearch.research_queries(_queries(topic, context))

    brief = RESEARCH_BRIEF.format(
        topic=topic, context=context, search_results=bundle,
    )

    research, _ = llm_client.chat(
        model=RESEARCH_MODEL,
        system=RESEARCH_SYSTEM,
        messages=[{"role": "user", "content": brief}],
        max_tokens=MAX_TOKENS,
    )

    if not research:
        research = bundle  # Notfall: Rohmaterial weiterreichen

    # Fallback: URLs im Freitext, falls die Suche nichts geliefert hat
    if not sources:
        sources = llm_client.extract_urls(research)

    return {"research": research, "sources": sources[:10]}
