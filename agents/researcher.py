# agents/researcher.py
# Agent 1: Recherche – holt per Web-Search belegte Fakten & Quellen.
# Output: {"research": str, "sources": [str]}
import os

import anthropic

from config import RESEARCH_MODEL, RESEARCH_SYSTEM, RESEARCH_BRIEF, MAX_TOKENS


def run(topic: str, context: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    brief = RESEARCH_BRIEF.format(topic=topic, context=context)

    response = client.messages.create(
        model=RESEARCH_MODEL,
        max_tokens=MAX_TOKENS,
        system=RESEARCH_SYSTEM,
        messages=[{"role": "user", "content": brief}],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5,
        }],
    )

    research = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    sources = _extract_sources(response)
    return {"research": research, "sources": sources}


def _extract_sources(response) -> list[str]:
    """Zieht URLs aus den server-side-Search-Citations (falls vorhanden)."""
    urls: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "web_search_tool_result":
            for hit in getattr(block, "content", []) or []:
                url = getattr(hit, "url", None)
                if url and url not in urls:
                    urls.append(url)
    # Fallback: URLs im Freitext
    if not urls:
        import re
        for block in response.content:
            if getattr(block, "type", None) == "text":
                for m in re.findall(r"https?://\S+", block.text):
                    if m not in urls:
                        urls.append(m)
    return urls[:10]
