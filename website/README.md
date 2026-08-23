# 135er-Grow Central – Project Website

Die statische Projektseite unter `website/` ist die öffentliche Präsentationsfläche von 135er-Grow Central.

**Website-Version:** `alpha-0.7.5`

**Dokumentierte validierte Raspberry-Pi-Basis:** `Build 85`

> **Status: ALPHA / HARDWAREVALIDIERUNG** – ein neuer Workflow-Lauf oder ein neuer Commit gilt nicht automatisch als neuer validierter Hardwarestand.

## Aktueller Stand – 23.08.2026

Die frühere öffentliche Build-70/71/72-Roadmap ist überholt. Der aktuelle `master` enthält inzwischen:

- die nach Build 85 validierte Grow-Central-Basis;
- die weiterentwickelte Geräte-Persistenz sowie verschlüsselte wiederverwendbare FRITZ!-Zugangsdaten;
- Stromkosten aus der erhaltenen Gesamtenergie, sodass historische Kosten auch bei ausgeschalteter Steckdose sichtbar bleiben;
- No-Cache-Liveprüfung und Offline-Ansicht bei Menüwechseln;
- lokales authentifiziertes Tapo-Onboarding mit dauerhafter Geräteübernahme;
- Cloud-/Server-Installer V6;
- ein signiertes APT-Repository unter `https://repo.dezender.de/apt`;
- Bereinigung alter/konfligierender Grow-Central-APT-Quellen im Bootstrap;
- einen erneut ausgelösten aktuellen Raspberry-Pi-Image-Build.

Neue Buildnummern werden auf der Website erst dann als **validiert** bezeichnet, wenn der zugehörige Image- und Hardwaretest tatsächlich abgeschlossen ist.

Details: [`docs/RELEASE_PIPELINE.md`](../docs/RELEASE_PIPELINE.md)

## Distribution

Die Website veröffentlicht über den Deploy-Workflow zusätzlich die aktuellen Server-Hilfsskripte:

- `135ercloud-server-install.sh` – aktueller Cloud-/Server-Installer V6;
- `setup-135ercloud-apt-repo.sh` – Einrichtung des signierten dezender.de-APT-Repositories.

Der APT-Client verwendet einen dedizierten `Signed-By`-Keyring. Legacy-Quellen werden vor dem Einrichten der kanonischen Quelle bereinigt, damit keine widersprüchlichen `Signed-By`-Definitionen bestehen bleiben.

## Mobile-Architektur

Mobile bleibt ein WebGUI-Client und **kein Ersatz für den Raspberry Pi**. Der Raspberry Pi bleibt die autoritative lokale Instanz für Gerätezugriff, Policy und Automation. Optional kann die Server-Version einen abgesicherten Remote-Zugriff bereitstellen.

## Design

Die Website orientiert sich direkt am verbindlichen Show- und Test-Design der Grow-Central-GUI: technische Statuskarten, HUD-Panels, grün-cyanfarbene Zustände sowie responsive Ansichten für Desktop, Tablet und Smartphone.

Die öffentliche Website bleibt technisch und sicherheitlich von der lokalen Steueroberfläche getrennt. Sie enthält keine lokalen Gerätezugangsdaten und keine direkten lokalen Steuerendpunkte.

## Branding und GUI-Vorschau

Verwendete Markenassets:

- `assets/brand/135er-grow-central-lockup-v0.9.png`
- `assets/brand/135er-grow-central-logo.png`
- `assets/brand/135er-grow-central-mark.png`

GUI-Vorschauen:

- `assets/gui/local-desktop-v0.9.png`
- `assets/gui/local-tablet-v0.9.png`
- `assets/gui/local-mobile-v0.9.png`
- `assets/gui/cloud-desktop-v0.9.png`

## Produktions-Deployment auf dezender.de

Bestätigter Plesk-Webroot:

```text
/var/www/vhosts/dezender.de/httpdocs
```

`.github/workflows/deploy-website-sftp.yml` veröffentlicht bei Änderungen an `website/**` sowie an den veröffentlichten Installationsskripten automatisch nach dezender.de. Vor dem Upload werden die kanonischen Skripte aus `scripts/` in den Website-Root kopiert.

Die SFTP-Zugangsdaten liegen ausschließlich als GitHub Actions Secrets vor und werden nicht in Website oder Repository geschrieben.

## Lokale Vorschau

```bash
cd website
python3 -m http.server 8000
```

Danach `http://localhost:8000` im Browser öffnen.
