import sqlite3
import requests

# API-Endpunkt
url = "https://restcountries.com/v3.1/all?fields=name,capital,translations"

# Daten abrufen
response = requests.get(url)
data = response.json()

# Datenbank erstellen
conn = sqlite3.connect("countries.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY,
    name_de TEXT NOT NULL,
    capital TEXT
)
""")

# Daten einfügen
id_counter = 1
for country in data:
    name_de = country.get("translations", {}).get("deu", {}).get("common", "")
    capital = country.get("capital", [""])[0] if country.get("capital") else ""
    cursor.execute("INSERT INTO countries (id, name_de, capital) VALUES (?, ?, ?)",
                   (id_counter, name_de, capital))
    id_counter += 1

conn.commit()
conn.close()

print("Datenbank 'countries.db' erfolgreich erstellt und gefüllt.")
