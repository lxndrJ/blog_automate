import sqlite3

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect("themes.db")
cursor = conn.cursor()

# Tabelle erstellen
cursor.execute("""
CREATE TABLE IF NOT EXISTS themes (
    id INTEGER PRIMARY KEY,
    theme TEXT NOT NULL,
    theme_category TEXT NOT NULL
)
""")

# Themen nach Kategorien
categories = {
    "Kultur und Traditionen": [
        "Volksfeste und Bräuche", "Trachten und Kleidung", "Musiktraditionen", "Tanzformen",
        "Architektur und Baukunst", "Feiertage und ihre Ursprünge", "Religiöse Rituale",
        "Dialekte und Sprachvielfalt", "Handwerkskunst", "Theater und Oper", "Literaturgeschichte",
        "Märchen und Sagen", "Symbolik in der Kultur", "Familienstrukturen", "Hochzeitsbräuche"
    ],
    "Kulinarische Spezialitäten": [
        "Regionale Gerichte", "Street Food", "Esskulturen im Vergleich", "Historische Rezepte",
        "Getränke und Braukunst", "Käse- und Wurstsorten", "Süßspeisen und Backtraditionen",
        "Essensrituale", "Saisonale Küche", "Essensetikette", "Vegetarische Spezialitäten",
        "Fischgerichte", "Brotvielfalt", "Gewürze und Kräuter", "Kulinarische Feste"
    ],
    "Natur und Landschaft": [
        "Nationalparks", "Gebirge und Wanderwege", "Seen und Flüsse", "Küstenlandschaften",
        "Flora und Fauna", "Klimazonen", "Naturphänomene", "Nachhaltiger Tourismus",
        "Schutzgebiete", "Landwirtschaftliche Regionen", "Wälder und Forstwirtschaft",
        "Geologische Besonderheiten", "Vogelbeobachtung", "Sternenhimmel und Astronomie",
        "Naturfotografie"
    ],
    "Geschichte": [
        "Antike Kulturen", "Mittelalterliche Städte", "Kolonialgeschichte", "Kriege und Konflikte",
        "Revolutionen", "Industrialisierung", "Archäologische Funde", "Historische Persönlichkeiten",
        "Geschichte der Bildung", "Frauen in der Geschichte", "Migration und Diaspora",
        "Geschichte der Religionen", "Geschichte der Technik", "Zeitgeschichte",
        "Museen und Gedenkstätten"
    ],
    "Reisetipps": [
        "Geheimtipps für Städtereisen", "Budgetreisen", "Nachhaltiges Reisen", "Backpacking-Routen",
        "Familienfreundliche Reiseziele", "Kulinarische Reiserouten", "Kulturreisen",
        "Abenteuerurlaub", "Wellness und Erholung", "Reiseplanung und Apps", "Sicherheit auf Reisen",
        "Unterkunftsarten", "Transportmittel im Vergleich", "Sprachbarrieren überwinden",
        "Reisedokumente und Visa"
    ],
    "Wirtschaft und Innovation": [
        "Start-ups und Gründerkultur", "Technologische Entwicklungen", "Nachhaltige Unternehmen",
        "Arbeitsmarkttrends", "Digitalisierung", "Industriegeschichte", "Energiequellen",
        "Bildung und Innovation", "Wirtschaftspolitik", "Exportprodukte", "Finanzwesen",
        "Infrastrukturprojekte", "Forschungseinrichtungen", "Zukunftstechnologien",
        "Unternehmenskultur"
    ],
    "Besondere Persönlichkeiten": [
        "Künstler und Kreative", "Wissenschaftler", "Politiker", "Sportler", "Unternehmer",
        "Aktivisten", "Entdecker und Reisende", "Philosophen", "Musiker und Komponisten",
        "Visionäre und Erfinder"
    ]
}

# Daten einfügen
id_counter = 1
for category, themes in categories.items():
    for theme in themes:
        cursor.execute("INSERT INTO themes (id, theme, theme_category) VALUES (?, ?, ?)",
                       (id_counter, theme, category))
        id_counter += 1

# Änderungen speichern und Verbindung schließen
conn.commit()
conn.close()

print("Datenbank 'themes.db' erfolgreich erstellt und gefüllt.")
