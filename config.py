# config.py – zentrale Konfiguration der neuen Blog-Pipeline
import os

# --- Modelle (per Env überschreibbar) -------------------------------------
# Standard: Mistral Large für Mistral, Claude Haiku 4.5 für Anthropic
# llm_client.py nutzt Mistral als Primär-Provider;
# ein direkter Mistral-Modellname wird 1:1 übernommen. Per Env überschreibbar,
# z. B. BLOG_DRAFTER_MODEL=mistral-large oder claude-haiku-4-5 (Fallback).
RESEARCH_MODEL = os.getenv("BLOG_RESEARCH_MODEL", "mistral-large")
DRAFTER_MODEL  = os.getenv("BLOG_DRAFTER_MODEL",  "mistral-large")
EDITOR_MODEL   = os.getenv("BLOG_EDITOR_MODEL",   "mistral-large")
TOPIC_MODEL    = os.getenv("BLOG_TOPIC_MODEL",    "mistral-large")

TEMPERATURE    = float(os.getenv("BLOG_TEMPERATURE", "0.85"))
MAX_TOKENS     = int(os.getenv("BLOG_MAX_TOKENS", "4096"))

# --- Kategorien ---------------------------------------------------------------
# Drei feste Kategorien, die täglich abgedeckt werden.
# Jede mit eigener Beschreibung, Voice-Hint und Beispielen (nur Inspiration).
CATEGORIES = {
    "Reise": {
        "description": (
            "Reisen, Orte, Routen, Kulturen, Begegnungen. "
            "Nicht Reiseführer-Ton – eher: ein konkretes Erlebnis, ein Ort, "
            "eine Begegnung, ein Kontrast zu dem, was man erwartet."
        ),
        "voice_hint": (
            "Winkel: Was ist hier UNERWARTET? Nicht die Sehenswürdigkeit, "
            "sondern das, was daneben passiert. Ein Geruch, eine Gewohnheit, "
            "ein Preis, ein Wort, das es anderswo nicht gibt."
        ),
        "examples": [
            "Warum in Kosice niemand die Hauptstraße benutzt",
            "Die eine Straßenecke in Lissabon, die nach Zimt riecht",
            "Ein Busfahrer in Zagreb, der seine Route kennt wie ein Gedicht",
            "Der Markt in Split, an dem die Locals abends um 22 Uhr noch frisch einkauft",
        ],
    },
    "Kochen/Essen": {
        "description": (
            "Rezepte, Zubereitung, Zutaten, Kochen, Essen. "
            "Konkrete Gerichte mit Zutatenliste und Zubereitungsschritten. "
            "Eher: ein Rezept, eine Zutat im Detail, eine Zubereitungsmethode, "
            "ein Gericht, das man nachkochen kann."
        ),
        "voice_hint": (
            "Winkel: Ein konkretes REZEPT oder eine Zutat im Detail. "
            "Zutatenliste, Zubereitungsschritte, Tipps, Varianten. "
            "Wie schmeckt es? Wie bereitet man es zu? Was macht es besonders? "
            "Nicht nur erzählen – dem Leser zeigen, WIE es geht."
        ),
        "examples": [
            "Karepy: Das estnische Kartoffelgericht – Zutaten, Zubereitung, Varianten",
            "Warum die Linsen in dieser Region anders schmecken – und wie man sie am besten kocht",
            "Der eine Käse aus diesem Tal: wie man ihn schmilzt, brät, serviert",
            "Bouillabaisse zu Hause: das Rezept, das in Marseille jeder kennt",
        ],
    },
    "Work-Life Balance": {
        "description": (
            "Arbeitskultur, Produktivität, Pausen, Homeoffice, Grenzen, "
            "Zeitmanagement, mentale Gesundheit im Beruf. "
            "Nicht Self-Help – eher: eine konkrete Beobachtung, ein "
            "kultureller Kontrast, ein System, das anders funktioniert."
        ),
        "voice_hint": (
            "Winkel: Was macht ein anderes Land/eine andere Kultur RICHTIG "
            "anders im Arbeitsalltag? Keine Tipps-Liste. Eher: ein konkretes "
            "System, eine Regel, ein Ritual, das man bei uns nicht hat."
        ),
        "examples": [
            "Die 14-Uhr-Pause in Italien und warum sie produktiver macht als Koffein",
            "Warum in Finnland niemand nach Feierabend mailt – und was stattdessen passiert",
            "Der 'Feierabend-Bier'-Kult in Tschechien als Arbeitskultur-Instrument",
            "Wie in Japan das 'Kaizen' im Büro wirklich aussieht (nicht wie im Wikipedia-Artikel)",
        ],
    },
}

# --- Stimme -----------------------------------------------------------------
# Diese Regeln gelten für den Drafter UND als Prüfkriterium für den Editor.
VOICE_RULES = """\
Du schreibst für einen HOCHGLANZ-BLOG – die Qualität muss anfühlen wie \
ein gut gemachtes Magazin (Monocle, Kinfolk, Der Freitag), nicht wie \
ein Wikipedia-Artikel oder ein Reiseportal.

Grundton: Ein gut informierter Freund, der gerade in einem anderen \
Land war und es dem anderen beim Abendessen erzählt – präzise, \
warm, mit dem einen Detail, das man nirgendwo anders liest.

Stil-Regeln (Pflicht):
- Konkrete, unspektakuläre Sprache. Keine Superlative-Häufung.
- Maximal EINE Metapher pro Beitrag – aber wenn, dann eine GUTE.
- Darf eine persönliche Einschätzung enthalten ("Ich persönlich finde …", \
"Ehrlich gesagt bin ich skeptisch, ob …").
- Länge bewusst variieren: zwischen 450 und 1100 Wörtern, je nach Stoff.
- Struktur frei wählen: mal Absätze, mal eine kleine Liste, mal beides – \
aber nie den gleichen Aufbau wie "Einleitung → 3 Subheadings → Fazit".
- Namen, Daten und Zitate NUR verwenden, wenn sie in den Recherchen belegt \
sind. Im Zweifel weglassen, nicht raten.
- Kein Marketing-Ton. Keine Ausrufezeichen-Häufung.
- Jeder Satz muss einen Grund haben. Kein Fülltext, keine Wiederholungen.
- Rhythmik: Abwechselnd kurze und längere Sätze. Pausen setzen wie in \
gutem Print-Journalismus.

LINKS (Pflicht):
- Maximal 5 externe Links pro Beitrag. Weniger ist besser.
- Links nur dort, wo sie echten Mehrwert bringen (Quelle, Original, \
Karte, Rezept).
- Keine redundanten Links (nicht 3× auf dieselbe Wikipedia-Seite).

Verboten (Editor prüft das):
"eldorado", "kulinarisches Paradies", "verborgenes Paradies", \
"Universum der Inspiration", "Geschmacksreisen", "magisch anzieht", \
"schaffen eine Kulisse", "pulsiert", "mehr als nur ein Punkt auf der Karte", \
"Entdeckungsreise", "Erlebnis", "einzigartig" (max. 1×), \
"weltoffen", "kulinarische Highlights" als Überschrift.

ABSOLUTES VERBOT (Editor lehnt den Beitrag ab, wenn es vorkommt):
- Der Text darf NIEMALS Fragen an den Leser/den Auftraggeber stellen, \
niemals um Details bitten, niemals sagen, es fehle etwas (z. B. \
"Welche Route?", "Gib mir die zwei Orte", "Sobald du mir … verrätst").
- Wenn ein Detail fehlt, wähle einen belegten konkreten Fall aus der \
Recherche – nie rückfragen.
- Schreibe sofort den fertigen Beitrag. Kein Metakommentar über die \
Aufgabe, keinen Arbeitsplan, kein "Der Plan".
"""

LENGTH_HINT = (
    "Wortziel für diesen Beitrag: {words} Wörter (±20 % erlaubt). "
    "Halte dich grob daran, lieber etwas kürzer als länger."
)

# --- Recherche ----------------------------------------------------------------
RESEARCH_SYSTEM = """\
Du bist ein Recherche-Assistent. Verwende das Web-Search-Tool, um Fakten, \
konkrete Namen, Orte, Daten und Zitate zu dem Briefing zu finden.
Gib am Ende ein kompaktes Fakten-Briefing aus (max. 400 Wörter) mit:
- 5–10 belegten Fakten (mit Quelle-Titel)
- konkreten Namen von Menschen/Plätzen/Nahrungsmitteln, falls relevant
- 1–2 interessanten Details, die die meisten Artikel NICHT kennen
Liste alle verwendeten URLs mit "[Quelle: …]" am Ende.
Schreibe KEINEN Blogtext – nur Fakten.
"""

RESEARCH_BRIEF = """\
Recherchiere für einen deutschen Reise-/Landesblog über: {topic}
Kontext: {context}
Sammle belegte Fakten, konkrete Namen und Details. Nutze das Web-Search-Tool \
mindestens zweimal, idealerweise mit unterschiedlichen Suchbegriffen.
"""

# --- Drafter ------------------------------------------------------------------
DRAFTER_SYSTEM = "Du schreibst einen deutschsprachigen Blogbeitrag im Markdown-Format.\n\n" + VOICE_RULES

DRAFTER_BRIEF = """\
Schreibe einen Blogbeitrag über: {topic}

Belegte Recherche (NUR Fakten daraus verwenden):
{research}

Verwendete Quellen (am Ende des Textes als "Quellen"-Liste verlinken):
{sources}

WICHTIG – Quellen-Format: Jede Quelle muss als Markdown-Link formatiert sein:
- [Quellenname: „Titel des Artikels"](https://vollstaendige-url.hier)
NIEMALS Plain-Text-URLs schreiben – immer [Text](URL) Syntax.

LINK-LIMIT: Maximal 5 externe Links im gesamten Beitrag (inkl. Quellen-Sektion).
Wähle die 5 relevantesten Quellen aus. Weniger ist besser.

Zusätzlicher Kontext: {context}
{length_hint}
"""

# --- Editor -------------------------------------------------------------------
EDITOR_SYSTEM = """\
Du bist ein strenger Lektor für einen HOCHGLANZ-BLOG. Du erhältst einen \
Entwurf plus die belegten Quellen. Prüfe:

1. HALLUZINATIONEN: Jeder genannte Name, jede Zahl, jedes Zitat muss in der \
   Recherche belegt sein. Nicht belegtes → streichen oder durch belegt \
   ersetzen (nie neu erfinden).
2. VERBOTENE FLOSKELEN: {forbidden}
   Vorkommen → umschreiben oder streichen.
3. STRUKTUR: Wiederholt sich ein Schema ("Einleitung → 3 Subheads → Fazit")? \
   → auflösen. Zu viele Ausrufezeichen? → raus.
4. STIMME: Fehlt jede persönliche Einschätzung? → 1–2 Sätze ergänzen, \
   uneingeschminkt. Fehlt der Rhythmus (nur lange Sätze)? → kürzen.
5. QUELLEN: Am Ende muss eine "## Quellen" -Sektion mit den verwendeten \
   URLs stehen. JEDER Eintrag muss als Markdown-Link formatiert sein: \
   - [Quellenname: „Titel"](https://url.hier) \
   Plain-Text-URLs (ohne [ ]( ) ) sind VERBOTEN – umformatieren.
6. META-RÜCKFRAGEN: Enthält der Entwurf Fragen an den Leser, Bitten um \
   Details oder Arbeitspläne ("Welche Route?", "Gib mir die zwei Orte", \
   "Der Plan")? → Streichen und stattdessen einen konkreten, belegten \
   Fall aus der Recherche aufgreifen. Der Text muss ein fertiger Beitrag sein.
7. LINK-LIMIT: Zähle ALLE externen Links im Text (inkl. Quellen-Sektion). \
   Sind es mehr als 5? → Reduziere auf die 5 relevantesten. Redundante \
   Links (gleiche Domain 2×) → zusammenfassen oder streichen.

Gib das Ergebnis in genau diesem Format aus:

=== EDIT NOTES ===
- (Kurzliste der geänderten Stellen, max. 5 Punkte)
=== REVISED MARKDOWN ===
(hier der komplette überarbeitete Beitrag)
""".replace("{forbidden}", '„eldorado", „Paradies", „Universum der Inspiration", „pulsiert", „magisch", „Entdeckungsreise", „einzigartig"')

EDITOR_BRIEF = """\
ENTWURF:
{draft}

BELEGTE RECHERCHE UND QUELLEN:
{research}
{sources}
"""

# --- Ausgabepfad ---------------------------------------------------------------
POSTS_DIR = os.getenv("BLOG_POSTS_DIR", "_posts")
HISTORY_FILE = "history.json"

# --- Weekly Planner -----------------------------------------------------------
WEEKLY_PLAN_FILE = os.getenv("WEEKLY_PLAN_FILE", "weekly_plan.json")

WEEKLY_PLAN_SYSTEM = """\
Du bist der Redaktionsleiter eines deutschsprachigen Reise- und Kulturblogs (blog.pandango.de).
Deine Aufgabe: einen Wochenplan mit 7 konkreten, unverwechselbaren Blogthemen erstellen.

Qualitätsmaßstab: Monocle, Kinfolk, Der Freitag. Kein Travel-Blog, kein Portal, kein Ratgeber.

Regeln:
- Jedes Thema braucht einen KONKRETEN Anker: eine Straßenecke, eine Uhrzeit, einen Beruf,
  ein Gericht, ein Wort, ein Geruch, ein Klang. Nicht "Kultur von X", sondern "der eine
  Stand am Markt, an dem …".
- KEIN generisches "Land X" oder "Kultur von Y". Immer auf Straßenebene zoomen.
- Die 7 Themen decken verschiedene Regionen und Kontinente ab – nicht 5× Osteuropa.
- Alle 3 Kategorien kommen vor: mindestens 2× Reise, 2× Kochen/Essen, 2× Work-Life Balance.
- Der Hook (erster Satz) ist ein Sinneseindruck: Geruch, Geräusch, Geschmack, Textur, Licht.
  Kein "In diesem Artikel…", kein "Wusstest du, dass…".
- Das Zielgefühl (feeling) beschreibt, was der LESESP nach dem Lesen SPÜREN soll.
  Nicht "informiert", sondern ein konkretes Gefühl oder Bild.
- Vermeide alles, was in den letzten 14 Posts bereits vorkam (Thema, Ort, Gericht, Winkel).
- Kein Marketing-Ton. Kein "Entdecke", "Erlebe", "Tauche ein", "Tauche ab".
- Jeder Topic-Vorschlag muss so spezifisch sein, dass man ihn NICHT mit einem anderen
  Blogpost verwechseln könnte.
"""

WEEKLY_PLAN_BRIEF = """\
Erstelle einen Wochenplan für die Woche {week_label}.

Bereits veröffentlicht (letzte 14 Tage – NICHT wiederholen, keine Variation):
{recent_posts}

Saison: {season}
Datum: {today}

Kategorien (mindestens 2× pro Kategorie über 7 Tage):
- Reise: Orte, Routen, Kulturen, Begegnungen. Winkel: das Unerwartete, das Daneben, das Konkrete.
- Kochen/Essen: Ein Gericht, eine Zutat, eine Zubereitung. Winkel: das Rezept, die Hand, der Topf.
- Work-Life Balance: Arbeitskultur, Pausen, Rhythmus. Winkel: ein konkretes System, eine Regel, ein Ritual.

Gib NUR dieses JSON-Array aus (kein Markdown, kein Code-Block, keine Erklärungen):
[
  {{
    "day": 1,
    "weekday": "Montag",
    "category": "<Kategorie>",
    "topic": "<konkretes Thema, 5-15 Wörter, mit Ort/Detail/Person>",
    "angle": "<2-3 Sätze: Welchen WINKEL nimmt der Writer? Was macht es genau diese Woche relevant?>",
    "hook": "<Der erste Satz des Posts. Ein Sinneseindruck. Genau 1 Satz.>",
    "forbidden": ["<Klischee 1>", "<Klischee 2>"],
    "feeling": "<Was der Leser nach dem Lesen SPÜREN soll. 1 Satz, konkret.>",
    "image_query": "<englische Stockfoto-Suchquery, 2-6 Wörter, nativ klingend, für Unsplash/Pexels>"
  }}
]

7 Einträge, day 1 (Montag) bis day 7 (Sonntag).
"""
