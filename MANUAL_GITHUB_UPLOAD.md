# Manueller GitHub-Upload – 135er-Grow Central

Dieses Archiv ist für den manuellen Upload zu GitHub vorbereitet.

## GitHub-Webseite

1. Archiv entpacken.
2. Auf GitHub ein neues Repository `135er-Grow Central` erstellen.
3. Beim Erstellen **kein zusätzliches README, .gitignore oder LICENSE** erzeugen.
4. Im leeren Repository **uploading an existing file** wählen.
5. Den gesamten Inhalt des Ordners `135er-Grow-Central` in das Upload-Feld ziehen.
6. Commit-Nachricht: `Initial upload - 135er-Grow Central v0.3.1`
7. **Commit changes**.

## PowerShell / GitHub CLI

```powershell
cd .\135er-Grow-Central
git init
git branch -M main
git add .
git commit -m "Initial upload - 135er-Grow Central v0.3.1"
gh repo create jygnw29kms-bit/135er-Grow Central --public --source=. --remote=origin --push
```

Falls das GitHub-Repository bereits existiert:

```powershell
cd .\135er-Grow-Central
git init
git branch -M main
git add .
git commit -m "Initial upload - 135er-Grow Central v0.3.1"
git remote add origin https://github.com/jygnw29kms-bit/135er-Grow Central.git
git push -u origin main
```

## Inhalt

- Raspberry-Pi/FastAPI-Backend
- DF100M BLE-Adapter
- Future-HUD-Webinterface
- SQLite-Grundlage
- systemd-Service
- Tests
- GitHub-Actions-Workflow
- GitHub-Issue-Template
- README und Projektdokumentation
- Architektur, Installation und API
- Reverse-Engineering-Dokumentation
- Roadmap und Troubleshooting
- Security und Contributing
- Quellen und Referenzen
- MIT-Lizenz

## Quellen

Siehe `docs/SOURCES.md`.

Die dort genannten Mars-Hydro-Links, Mars Legacy, KillerInk/GrowFanController
sowie die eigenen APK-Beobachtungen sind getrennt gekennzeichnet.

## Hinweis zum DF100M

`DF100M` ist nur die technische Gerätebezeichnung und nicht der Projektname.
Der Projektname lautet **135er-Grow Central**.

Die dokumentierten UUIDs und Begriffe wie `wind_set_speed` sind
Reverse-Engineering-Anhaltspunkte und keine offizielle Mars-Hydro-
Protokolldokumentation.
