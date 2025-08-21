#!/bin/bash

# Aktuelles Datum im Format YYYYMMDD und YYYY-MM-DD
DATE=$(date +"%Y%m%d")
DATE_HUMAN=$(date +"%Y-%m-%d")

# Finde die Markdown-Datei mit dem heutigen Datum
FILE=$(ls ./_posts/${DATE}_*.md 2>/dev/null)

# Prüfen, ob Datei existiert
if [ -z "$FILE" ]; then
  echo "Keine Markdown-Datei für heute gefunden."
  exit 1
fi

# Git-Befehle ausführen
git add "$FILE"
git commit -m "Automatischer Blogpost vom $DATE_HUMAN"
git push

echo "Blogpost '$FILE' erfolgreich zu GitHub gepusht."
