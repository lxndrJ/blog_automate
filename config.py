# config.py – zentrale Konfiguration der neuen Blog-Pipeline
import os

# --- Modelle (per Env überschreibbar) -------------------------------------
# Modellnamen können hier je Account/Katalog abweichen – per Env überschreibbar.
RESEARCH_MODEL = os.getenv("BLOG_RESEARCH_MODEL", "claude-haiku-4-5")
DRAFTER_MODEL  = os.getenv("BLOG_DRAFTER_MODEL",  "claude-haiku-4-5")
EDITOR_MODEL   = os.getenv("BLOG_EDITOR_MODEL",   "claude-haiku-4-5")
TOPIC_MODEL    = os.getenv("BLOG_TOPIC_MODEL",    "claude-haiku-4-5")

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
            "sondern das, was daneben passiert. Ein Geruch, eine Uhrzeit, "
            "ein Preis, ein Wort, das es anderswo nicht gibt."
        ),
        "examples": [
            "Der 4-Uhr-Asse in Thessaloniki und wer dort einkauft",
            "Warum in Kosice niemand die Hauptstraße benutzt",
            "Die eine Straßenecke in Lissabon, die nach Zimt riecht",
            "Ein Busfahrer in Zagreb, der seine Route kennt wie ein Gedicht",
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
Du schreibst wie ein gut informierter Freund, der gerade in einem anderen \
Land war und es dem anderen beim Abendessen erzählt.

Stil-Regeln (Pflicht):
- Konkrete, unspektakuläre Sprache. Keine Superlative-Häufung.
- Maximal EINE Metapher pro Beitrag.
- Darf eine persönliche Einschätzung enthalten ("Ich persönlich finde …", \
"Ehrlich gesagt bin ich skeptisch, ob …").
- Länge bewusst variieren: zwischen 450 und 1100 Wörtern, je nach Stoff.
- Struktur frei wählen: mal Absätze, mal eine kleine Liste, mal beides – \
aber nie den gleichen Aufbau wie "Einleitung → 3 Subheadings → Fazit".
- Namen, Daten und Zitate NUR verwenden, wenn sie in den Recherchen belegt \
sind. Im Zweifel weglassen, nicht raten.
- Kein Marketing-Ton. Keine Ausrufezeichen-Häufung.

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

Zusätzlicher Kontext: {context}
{length_hint}
"""

# --- Editor -------------------------------------------------------------------
EDITOR_SYSTEM = """\
Du bist ein strenger Lektor. Du erhältst einen Entwurf plus die belegten \
Quellen. Prüfe:

1. HALLUZINATIONEN: Jeder genannte Name, jede Zahl, jedes Zitat muss in der \
   Recherche belegt sein. Nicht belegtes → streichen oder durch belegt \
   ersetzen (nie neu erfinden).
2. VERBOTENE FLOSKELEN: {forbidden}
   Vorkommen → umschreiben oder streichen.
3. STRUKTUR: Wiederholt sich ein Schema ("Einleitung → 3 Subheads → Fazit")? \
   → auflösen. Zu viele Ausrufezeichen? → raus.
4. STIMME: Fehlt jede persönliche Einschätzung? → 1–2 Sätze ergänzen, \
   uneingeschminkt.
5. QUELLEN: Am Ende muss eine "## Quellen" -Sektion mit den verwendeten \
   URLs stehen. JEDER Eintrag muss als Markdown-Link formatiert sein: \
   - [Quellenname: „Titel"](https://url.hier) \
   Plain-Text-URLs (ohne [ ]( ) ) sind VERBOTEN – umformatieren.
6. META-RÜCKFRAGEN: Enthält der Entwurf Fragen an den Leser, Bitten um \
   Details oder Arbeitspläne ("Welche Route?", "Gib mir die zwei Orte", \
   "Der Plan")? → Streichen und stattdessen einen konkreten, belegten \
   Fall aus der Recherche aufgreifen. Der Text muss ein fertiger Beitrag sein.

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
