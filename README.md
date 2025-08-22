# blog_automate
AI generierter blog

## Automatisierte Blog-Generierung mit GitHub Actions

Dieses Repository enthält eine GitHub Action, die jeden Morgen um 5:00 Uhr UTC automatisch einen Blogbeitrag generiert.

### Setup

#### 1. GitHub Secrets konfigurieren

Fügen Sie die folgenden Secrets in Ihren GitHub Repository-Einstellungen hinzu:

- `ANTHROPIC_API_KEY`: Ihr API-Schlüssel für Anthropic Claude
- `UNSPLASH_ACCESS_KEY`: Ihr Access Key für die Unsplash API
- `BLOG_SYNC_TOKEN`: GitHub Personal Access Token für die Synchronisation mit dem blog.pandango.de Repository

#### 2. Erforderliche Dateien

Das Repository enthält:
- `generate_blog_post.py` - Hauptskript für die Blog-Generierung
- `requirements.txt` - Python-Abhängigkeiten
- `.github/workflows/generate-blog-post.yml` - GitHub Action Workflow für tägliche Blog-Generierung
- `.github/workflows/sync-posts.yml` - GitHub Action Workflow für die Synchronisation der _posts
- `countries.db` und `themes.db` - SQLite-Datenbanken mit Ländern und Themen

#### 3. GitHub Actions

Das Repository enthält zwei GitHub Actions:

##### Blog-Generierung (generate-blog-post.yml)
Die Action läuft automatisch jeden Tag um 5:00 Uhr UTC und:
1. Installiert Python-Abhängigkeiten
2. Führt das Blog-Generierungsskript aus
3. Committed und pushed die generierten Dateien

##### Posts-Synchronisation (sync-posts.yml)
Die Action wird bei Änderungen im `_posts` Ordner ausgelöst und:
1. Synchronisiert den `_posts` Ordner mit dem blog.pandango.de Repository
2. Behandelt hinzugefügte, geänderte und gelöschte Dateien korrekt
3. Committed und pushed die Änderungen zum Ziel-Repository

### Manuelle Ausführung

Sie können beide Actions auch manuell über den "Actions" Tab in GitHub ausführen:
- **Generate Daily Blog Post**: Für die manuelle Generierung eines Blogbeitrags
- **Sync Posts to Blog Repository**: Für die manuelle Synchronisation der _posts
