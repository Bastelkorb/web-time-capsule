# Web Time Capsule | Webseiten-Zeitkapsel

**Preserve the public websites that matter to you.**  
**Bewahre öffentliche Webseiten, die dir am Herzen liegen.**

[English](#english) · [Deutsch](#deutsch)

---

## English

Web Time Capsule helps you collect publicly accessible website URLs and submit them to the [Internet Archive Wayback Machine](https://web.archive.org/) for archiving.

### Download for Windows

Download the official **`WebTimeCapsule.exe`** from the [Releases page](https://github.com/Bastelkorb/web-time-capsule/releases/latest). Download only releases published by the project owner.

1. Download `WebTimeCapsule.exe` from the latest release.
2. Start the file. Keep its console window open while it works.
3. Follow the prompts and enter the public website address you want to scan.
4. Review the discovered URLs before submitting archive jobs.

### Features

- Discover internal links and available XML sitemaps on public HTTP/HTTPS websites.
- Optionally include relevant subdomains.
- Review the URL list before submitting archive requests.
- Detect and log redirects separately.
- Keep crawl errors and archive errors in separate lists.
- Offer another attempt for failed requests.
- Export results to CSV for review in spreadsheet software.

### Important information

- This repository distributes the **precompiled Windows executable only**. Application source code and build scripts are not published here.
- The absence of source code discourages straightforward reuse, but it cannot guarantee that a compiled program is impossible to analyse or reverse engineer.
- Automated Save Page Now requests may require Internet Archive S3 credentials. Enter them only in the program when requested. Never post secret keys in GitHub issues, screenshots, logs, or public files.
- The tool does not bypass logins, CAPTCHAs, or access restrictions. Respect website terms and access policies.
- A successful archive request does not guarantee that every page, image, script, or other resource was captured completely.
- The program cannot disable a redirect performed by a website. It records redirects to help you spot when the destination differs from the requested URL.

### Distribution and rights

This repository is for distributing official precompiled binaries. No open-source licence or permission to reuse, modify, or redistribute the program is granted by this README. Any use beyond downloading and running an official release requires permission from the rights holder, subject to applicable law.

---

## Deutsch

Die **Webseiten-Zeitkapsel** hilft dir dabei, öffentlich erreichbare Webseiten-Adressen zu sammeln und ihre Archivierung bei der [Wayback Machine des Internet Archive](https://web.archive.org/) anzustoßen.

### Download für Windows

Lade die offizielle **`WebTimeCapsule.exe`** auf der [Veröffentlichungsseite](https://github.com/Bastelkorb/web-time-capsule/releases/latest) herunter. Nutze nur Veröffentlichungen des Projektinhabers.

1. Lade `WebTimeCapsule.exe` aus der neuesten Veröffentlichung herunter.
2. Starte die Datei. Lass das Konsolenfenster geöffnet, solange das Programm arbeitet.
3. Folge den Abfragen und gib die öffentliche Website-Adresse ein, die du durchsuchen möchtest.
4. Prüfe die gefundenen URLs, bevor Archivierungsaufträge gesendet werden.

### Funktionen

- Interne Links und vorhandene XML-Sitemaps öffentlicher HTTP-/HTTPS-Websites finden.
- Bei Bedarf passende Unterdomains einbeziehen.
- Gefundene URL-Liste vor dem Senden der Archivierungsaufträge prüfen.
- Weiterleitungen erkennen und getrennt protokollieren.
- Suchfehler und Archivierungsfehler in getrennten Listen speichern.
- Fehlgeschlagene Anfragen auf Wunsch erneut versuchen.
- Ergebnisse als CSV für Tabellenprogramme exportieren.

### Wichtige Hinweise

- Dieses Repository stellt **nur die vorkompilierte Windows-EXE** bereit. Der Programmquellcode und Build-Skripte werden hier nicht veröffentlicht.
- Fehlender Quellcode erschwert die direkte Wiederverwendung, kann aber nicht garantieren, dass ein kompiliertes Programm grundsätzlich nicht analysiert oder zurückentwickelt werden kann.
- Für automatisierte Save-Page-Now-Aufträge können Zugangsdaten des Internet Archive erforderlich sein. Gib sie nur im Programm ein, wenn du dazu aufgefordert wirst. Veröffentliche niemals geheime Schlüssel in GitHub-Issues, Screenshots, Protokollen oder öffentlichen Dateien.
- Das Programm umgeht keine Anmeldungen, CAPTCHAs oder Zugriffsbeschränkungen. Beachte die Nutzungsbedingungen und Zugriffsvorgaben der jeweiligen Website.
- Ein erfolgreicher Archivierungsauftrag garantiert nicht, dass jede Seite, jedes Bild, jedes Skript und jede weitere Ressource vollständig gespeichert wurde.
- Eine vom Webserver ausgeführte Weiterleitung kann das Programm nicht abschalten. Es protokolliert Weiterleitungen, damit du erkennst, wenn das Ziel von der angefragten Adresse abweicht.

### Weitergabe und Nutzungsrechte

Dieses Repository dient ausschließlich der Verteilung der offiziellen, vorkompilierten Programmdatei. Durch diese README wird keine Open-Source-Lizenz und keine Erlaubnis erteilt, das Programm weiterzuverwenden, zu verändern oder weiterzuverbreiten. Jede Nutzung über das Herunterladen und Ausführen einer offiziellen Veröffentlichung hinaus bedarf der Zustimmung des Rechteinhabers, soweit das geltende Recht nichts anderes vorsieht.
