# blog_automate
AI generierter blog

## Automatisierte Blog-Generierung mit GitHub Actions

Dieses Repository enthält eine GitHub Action, die jeden Morgen um 5:00 Uhr UTC automatisch einen Blogbeitrag generiert.

### Setup

#### 1. GitHub Secrets konfigurieren

Fügen Sie die folgenden Secrets in Ihren GitHub Repository-Einstellungen hinzu:

- `ANTHROPIC_API_KEY`: Ihr API-Schlüssel für Anthropic Claude
- `UNSPLASH_ACCESS_KEY`: Ihr Access Key für die Unsplash API
- `BLOG_SYNC_TOKEN`: Personal Access Token mit Schreibzugriff auf das `blog.pandango.de` Repository (für die automatische Synchronisation)

#### 2. Erforderliche Dateien

Das Repository enthält:
- `generate_blog_post.py` - Hauptskript für die Blog-Generierung
- `requirements.txt` - Python-Abhängigkeiten
- `.github/workflows/generate-blog-post.yml` - GitHub Action Workflow für tägliche Blog-Generierung
- `.github/workflows/sync-posts.yml` - GitHub Action Workflow für Synchronisation der `_posts` mit dem Blog-Repository
- `countries.db` und `themes.db` - SQLite-Datenbanken mit Ländern und Themen

#### 3. GitHub Actions

Das Repository enthält zwei automatisierte Workflows:

##### Blog-Generierung (generate-blog-post.yml)
Die Action läuft automatisch jeden Tag um 5:00 Uhr UTC und:
1. Installiert Python-Abhängigkeiten
2. Führt das Blog-Generierungsskript aus
3. Committed und pushed die generierten Dateien

##### Blog-Synchronisation (sync-posts.yml)
Die Action wird automatisch ausgelöst bei Änderungen im `_posts` Ordner und:
1. Synchronisiert alle Dateien aus dem `_posts` Ordner mit dem `blog.pandango.de` Repository
2. Behandelt hinzugefügte, geänderte und gelöschte Dateien korrekt
3. Committed und pushed die Änderungen zum Ziel-Repository

**Hinweis:** Für die Synchronisation ist ein Personal Access Token (`BLOG_SYNC_TOKEN`) erforderlich, das Schreibzugriff auf das Ziel-Repository hat.

### Manuelle Ausführung

Sie können beide Actions auch manuell über den "Actions" Tab in GitHub ausführen:
- **Generate Daily Blog Post**: Erstellt sofort einen neuen Blogbeitrag
- **Sync Posts to Blog Repository**: Synchronisiert den aktuellen `_posts` Ordner manuell mit dem Blog-Repository
