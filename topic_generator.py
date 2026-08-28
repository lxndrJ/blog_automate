# topic_generator.py – AI-gestützter Themengenerator pro Kategorie
# Ersetzt die starren Templates in topics.py durch freie, kontextuelle Vorschläge.
# Fallback: Falls die API nicht erreichbar ist, greifen die alten Templates.

import json
import os
import random
import sys

import anthropic

from config import TOPIC_MODEL, CATEGORIES

# Fallback auf topics.py (alte Templates)
import topics as _legacy_topics


def generate(category: str, recent_titles: list[str] | None = None,
             cross_ref: str = "") -> dict:
    """Generiert ein spezifisches, kreatives Thema für die gegebene Kategorie.

    Args:
        category:     z. B. "Reise", "Kochen/Essen", "Work-Life Balance"
        recent_titles: Letzte 50 Titel (für Dedup)
        cross_ref:    Optionaler Kontext, z. B. der Reise-Post des Tages

    Returns:
        {"topic": str, "context": str, "base": str}
        – dieselbe Struktur wie topics.pick_topic()
    """
    cat_info = CATEGORIES.get(category, CATEGORIES.get("Reise", {}))
    description = cat_info.get("description", "allgemein")
    voice_hint = cat_info.get("voice_hint", "")
    examples = cat_info.get("examples", [])

    # Titel-Ausschluss-Liste
    title_block = ""
    if recent_titles:
        recent = recent_titles[-50:]
        title_block = (
            "\n\nBereits verwendete Titel (NICHT wiederholen, keine Variation davon):\n"
            + "\n".join(f"  - {t}" for t in recent)
        )

    # Cross-Referenz (z. B. Kochen-Post bezieht sich auf Reise-Post)
    cross_block = ""
    if cross_ref:
        cross_block = (
            f"\n\nWICHTIG: Der heutige Reise-Post behandelt: \"{cross_ref}\". "
            f"Verknüpfe dein Thema mit diesem Ort/Thema, wo es natürlich passt "
            f"(z. B. ein Gericht aus dieser Region, ein lokales Ritual, eine Zutat)"
            f"ohne zu groß auf die Details des Reise-Posts einzugehen wie zB die Uhrzeit etc.."
        )

    # Beispiel-Angel (keine Pflicht, nur Inspiration)
    example_block = ""
    if examples:
        example_block = (
            "\n\nBeispiele für die Art von Spezifität, die gesucht ist "
            "(NICHT direkt verwenden – nur als Orientierung für den Winkel):\n"
            + "\n".join(f"  - {e}" for e in examples[:5])
        )

    prompt = f"""Vorschlage EXAKT EIN spezifisches, ungewöhnliches Blog-Thema.

Kategorie: {category}
Beschreibung: {description}
{voice_hint}
{example_block}
{cross_block}
{title_block}

Regeln:
- KEIN generisches "Top 10" oder "Guide" oder "Ratgeber"
- Eher: ein konkreter Ort, ein Wort, ein Beruf, eine Zutat, eine Uhrzeit, ein Geruch, ein Konflikt, eine Frage ohne einfache Antwort
- Deutsch, 5–15 Wörter als Titel-Vorschlag
- Der Kontext (2–3 Sätze) soll dem Writer sagen, WELCHEN WINKEL er nehmen soll – nicht WAS er schreiben soll
- Keine Fragen an den Leser
- Keine Floskeln ("entdecke", "erlebe", "tauche ein")

ZUSÄTZLICH: Erstelle eine ENGLISCHE Suchquery (2–6 Wörter) für eine Stockfoto-Suche (Unsplash/Pexels),
die zum Thema passt. Die Query soll:
- Natürliches, spezifisches Englisch sein (keine Übersetzung, sondern eine nativ klingende Suchphrase)
- Konkrete Nomen/Adjektive enthalten (z. B. "thessaloniki morning market" statt "market")
- Für Unsplash/Pexels optimiert sein (dort werden englische Tags/Beschreibungen indexiert)

Gib NUR dieses JSON aus (kein Markdown, kein Code-Block):
{{"topic": "<deutscher Titel-Vorschlag>", "context": "<Winkel-Hinweis für den Writer>", "image_query": "<english stock photo search query>"}}
"""

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=TOPIC_MODEL,
            max_tokens=300,
            system="Du bist ein kreativer Themen-Editor für einen deutschsprachigen Blog. "
                   "Du schlägst immer UNERWARTETE, konkrete, persönliche Winkel vor. "
                   "Kein Marketing-Ton. Kein Generisches.",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(b.text for b in response.content if b.type == "text").strip()
        # JSON extrahieren (ggf. in Code-Block)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        topic = data.get("topic", "").strip()
        context = data.get("context", "").strip()
        image_query = data.get("image_query", "").strip()

        if not topic:
            raise ValueError("Leerer Topic-Vorschlag")

        return {
            "topic": topic,
            "context": context,
            "image_query": image_query,  # Englische Suchquery für Unsplash/Pexels
            "base": f"[AI] {category}: {topic}",  # für Dedup-Historie
        }

    except Exception as e:
        print(f"      ⚠ Topic-Generator fehlgeschlagen ({e}), Fallback auf Templates …",
              file=sys.stderr)
        # Fallback: alte kuratierte Templates
        return _legacy_topics.pick_topic(_legacy_topics.used_topics())


def generate_daily_set(recent_titles: list[str] | None = None) -> list[dict]:
    """Generiert den kompletten täglichen Satz: Reise → Kochen/Essen → Work-Life.

    Der Kochen-Post bekommt den Reise-Post als Cross-Referenz.
    """
    results = []

    # 1) Reise
    travel = generate("Reise", recent_titles)
    results.append({"category": "Reise", **travel})
    print(f"      [1/3] Reise:          {travel['topic']}")

    # 2) Kochen/Essen (mit Cross-Ref zum Reise-Post)
    food = generate("Kochen/Essen", recent_titles, cross_ref=travel["topic"])
    results.append({"category": "Kochen/Essen", **food})
    print(f"      [2/3] Kochen/Essen:   {food['topic']}")

    # 3) Work-Life Balance
    wlb = generate("Work-Life Balance", recent_titles)
    results.append({"category": "Work-Life Balance", **wlb})
    print(f"      [3/3] Work-Life:      {wlb['topic']}")

    return results
