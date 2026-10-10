# Web Time Capsule | Webseiten-Zeitkapsel

**Preserve the public websites that matter to you. / Bewahre öffentliche Webseiten, die dir am Herzen liegen.**

[English](#english) · [Deutsch](#deutsch)

---

## English

Web Time Capsule helps you discover public website pages and submit them to the [Internet Archive Wayback Machine](https://web.archive.org/) for archiving. It is designed to make the process easier to follow: URLs are collected first, redirects are checked, and failed jobs are logged separately so you can retry them.

### Download for Windows

The Windows executable is built automatically by GitHub Actions. Once a release is published:

1. Open the repository's **Releases** section.
2. Download `WebTimeCapsule.exe`.
3. Run it. Keep the console window open while it works.
4. Enter the public website address you want to scan.

Before the first release, you can download the executable from **Actions → Build Windows EXE → Artifacts** after a successful build.

### Features

- Crawl publicly accessible HTTP and HTTPS pages.
- Discover internal links and available XML sitemaps.
- Optionally include relevant subdomains.
- Review and save the collected URL list before submitting archive jobs.
- Detect live HTTP redirects and record them separately.
- Log crawl and archive failures to separate files.
- Ask before retrying failed requests.
- Save a CSV report that can be opened in spreadsheet software.
- Build a Windows executable automatically with GitHub Actions.

### Project files

- `website_archiv.py` — application source code
- `Start_Archivierung.bat` — starts the executable or Python source
- `build_exe.bat` — builds the Windows executable locally (Python required)
- `.github/workflows/build-windows.yml` — automated tests and Windows build
- `tests/` — automated tests
- `LICENSE` — MIT License
- `GITHUB-SETUP.txt` — repository setup instructions in English and German
- `GITHUB-HOCHLADEN.bat` — upload helper for the project folder
- `CREATE_RELEASE_V3.1.0.bat` — creates the first version tag and starts a release build

### Publish this project on GitHub

1. Create an **empty, public** GitHub repository named `web-time-capsule`.
2. Do not create an extra README, `.gitignore`, or license on GitHub; they are already included here.
3. Run `GITHUB-HOCHLADEN.bat`, copy the HTTPS clone URL of your new repository, and paste it into the window.
4. Git for Windows is required. GitHub may ask you to sign in through your browser.

### Build and release

Every push to `main` runs the tests and builds the Windows executable. Download it from **Actions → Build Windows EXE → Artifacts**.

After uploading the project, run `CREATE_RELEASE_V3.1.0.bat` and confirm when asked. If the workflow succeeds, GitHub publishes a `v3.1.0` release containing the executable and project files.

### Wayback Machine access

Automated Save Page Now requests may require Internet Archive S3 keys. Manage them at [Internet Archive S3 settings](https://archive.org/account/s3.php). Use the **Access Key** and **Secret Key**, not your normal account password. Never publish your secret key.

The program does not store the keys in the source code. You can enter them when prompted or provide them through the `IA_ACCESS_KEY` and `IA_SECRET_KEY` environment variables.

### Important notes

- This tool is intended for publicly accessible websites. It does not bypass logins, CAPTCHAs, or access restrictions.
- Follow each website's terms and access policies.
- External websites that are merely linked from the starting site are not crawled automatically.
- Dynamic content that requires JavaScript, sign-in, or special cookies may not be captured.
- A successful archive job does not guarantee that an entire website and all its resources have been saved completely.
- The tool cannot disable a server-side redirect. It detects redirects and logs them separately to help avoid mistaking the wrong page for a successful capture.
- Requests are spaced out to avoid unnecessarily burdening websites and archive services.

### Crawl only (without submitting archive jobs)

With Python installed, you can collect URLs without sending any archive requests:

```powershell
python website_archiv.py --start-url "https://example.com/" --crawl-only
```

### License

This project is distributed under the [MIT License](LICENSE).

---

## Deutsch

Die **Webseiten-Zeitkapsel** hilft dir dabei, öffentliche Webseiten und ihre Unterseiten zu finden und an die [Wayback Machine des Internet Archive](https://web.archive.org/) zur Archivierung zu übergeben. Damit du den Überblick behältst, sammelt das Programm zunächst die URLs, prüft Weiterleitungen und protokolliert fehlgeschlagene Aufträge getrennt. Fehlgeschlagene Versuche kannst du anschließend erneut starten.

### Download für Windows

Die Windows-EXE wird automatisch mit GitHub Actions erstellt. Sobald eine Veröffentlichung vorhanden ist:

1. Öffne den Bereich **Releases** des Repositorys.
2. Lade `WebTimeCapsule.exe` herunter.
3. Starte die Datei. Lass das Konsolenfenster geöffnet, solange das Programm arbeitet.
4. Gib die öffentliche Website-Adresse ein, die du durchsuchen möchtest.

Vor der ersten Veröffentlichung findest du die EXE nach einem erfolgreichen Build unter **Actions → Build Windows EXE → Artifacts**.

### Funktionen

- Öffentlich erreichbare HTTP- und HTTPS-Seiten durchsuchen.
- Interne Links und vorhandene XML-Sitemaps finden.
- Bei Bedarf passende Unterdomains einbeziehen.
- Die gefundene URL-Liste prüfen und speichern, bevor Archivierungsaufträge gesendet werden.
- HTTP-Weiterleitungen erkennen und separat protokollieren.
- Such- und Archivierungsfehler in getrennten Dateien speichern.
- Vor einem erneuten Versuch fehlgeschlagener Aufträge nachfragen.
- Einen CSV-Bericht erstellen, der sich mit Tabellenprogrammen öffnen lässt.
- Eine Windows-EXE automatisch über GitHub Actions bauen.

### Dateien im Projekt

- `website_archiv.py` — Programmquellcode
- `Start_Archivierung.bat` — startet die EXE oder den Python-Quellcode
- `build_exe.bat` — erstellt die Windows-EXE lokal (Python erforderlich)
- `.github/workflows/build-windows.yml` — automatische Tests und Windows-Build
- `tests/` — automatisierte Tests
- `LICENSE` — MIT-Lizenz
- `GITHUB-SETUP.txt` — Anleitung zur Einrichtung des Repositorys auf Deutsch und Englisch
- `GITHUB-HOCHLADEN.bat` — Helfer zum Hochladen des Projektordners
- `CREATE_RELEASE_V3.1.0.bat` — erstellt den ersten Versions-Tag und startet den Release-Build

### Dieses Projekt auf GitHub veröffentlichen

1. Erstelle ein **leeres, öffentliches** GitHub-Repository mit dem Namen `web-time-capsule`.
2. Erstelle auf GitHub keine zusätzliche README, `.gitignore` oder Lizenz; diese Dateien sind bereits im Paket enthalten.
3. Starte `GITHUB-HOCHLADEN.bat`, kopiere die HTTPS-Clone-Adresse des neuen Repositorys und füge sie im Fenster ein.
4. Git für Windows wird benötigt. Eventuell fordert GitHub dich auf, dich im Browser anzumelden.

### Build und Veröffentlichung

Bei jedem Upload auf den Branch `main` führt GitHub die Tests aus und baut die Windows-EXE. Du kannst sie unter **Actions → Build Windows EXE → Artifacts** herunterladen.

Nachdem du das Projekt hochgeladen hast, starte `CREATE_RELEASE_V3.1.0.bat` und bestätige die Rückfrage. Wenn der Workflow erfolgreich durchläuft, veröffentlicht GitHub ein Release `v3.1.0` mit der EXE und den Projektdateien.

### Zugriff auf die Wayback Machine

Für automatisierte Save-Page-Now-Aufträge können S3-Schlüssel des Internet Archive erforderlich sein. Du verwaltest sie in den [S3-Einstellungen des Internet Archive](https://archive.org/account/s3.php). Benötigt werden **Access Key** und **Secret Key**, nicht das normale Kontopasswort. Veröffentliche deinen Secret Key niemals.

Das Programm speichert die Schlüssel nicht im Quellcode. Du kannst sie bei der Abfrage eingeben oder über die Umgebungsvariablen `IA_ACCESS_KEY` und `IA_SECRET_KEY` bereitstellen.

### Wichtige Hinweise

- Das Tool ist für öffentlich erreichbare Webseiten gedacht. Es umgeht keine Anmeldungen, CAPTCHAs oder Zugriffssperren.
- Beachte die Nutzungsbedingungen und Zugriffsvorgaben der jeweiligen Website.
- Externe Websites, auf die von der Startseite nur verlinkt wird, werden nicht automatisch durchsucht.
- Dynamische Inhalte, die JavaScript, eine Anmeldung oder spezielle Cookies benötigen, können fehlen.
- Ein erfolgreicher Archivierungsauftrag garantiert nicht, dass eine ganze Website samt aller Ressourcen vollständig gespeichert wurde.
- Eine serverseitige Weiterleitung kann das Tool nicht abschalten. Es erkennt Weiterleitungen und protokolliert sie getrennt, damit nicht versehentlich die falsche Seite als Erfolg gilt.
- Zwischen Anfragen liegen Pausen, damit Websites und Archivierungsdienste nicht unnötig belastet werden.

### Nur durchsuchen (ohne Archivierungsaufträge)

Mit installierter Python-Version kannst du URLs sammeln, ohne Archivierungsaufträge zu senden:

```powershell
python website_archiv.py --start-url "https://example.com/" --crawl-only
```

### Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
