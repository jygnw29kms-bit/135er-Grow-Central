# 135er-Grow Central – Product Website

Die statische Projektseite unter `website/` ist die öffentliche Produkt- und Marketingseite von **135er-Grow Central**.

**Öffentliche URL:** `https://dezender.de/GC/`  
**Version:** `alpha-0.7.5`  
**Master-Anker:** `e339602`  
**Pi-Testkandidat:** `Build 118` / `pi-universal-alpha-0.7.5-118`  
**Status:** `CANDIDATE` – noch nicht hardwarevalidiert

Kanonische Quelle: [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

## Ziel der Website

Die Seite vermarktet und erklärt Grow Central als Local-First Steuerungs- und Automationsplattform für Grow-Umgebungen. Sie ist bewusst keine reine Entwicklerkonsole mehr, sondern eine professionelle Produktpräsentation mit:

- Produktnutzen und Plattformidee;
- Feature-Übersicht;
- Geräte- und Herstellerintegrationen;
- GrowCentral Nexus UI für Desktop, Touch/Kiosk und Mobile;
- Local-First Architektur und optionaler Cloud-Ebene;
- Sicherheits- und Capability-Modell;
- aktuellem Release- und Hardwareteststatus;
- FAQ, GitHub- und Release-Einstiegspunkten.

## Aktueller Stand – 24.08.2026

Build 117 war ein erfolgreicher Teststand, ist durch den konsolidierten e339-Master inzwischen überholt. Die Website zeigt deshalb Build 118 als nächsten Hardwaretest-Kandidaten und vermeidet die falsche Aussage, er sei bereits validiert.

Build 118 umfasst unter anderem:

- aktuelle Local-First GUI / First Boot / Netzwerk / Persistenz;
- FRITZ! Smart Home und Tapo;
- Logitech C920/UVC;
- firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung;
- bedingte V4L2-/Logitech-LED-Steuerung;
- Elecrow 7-Zoll Touch-Kiosk;
- Räume/Grow-Bereiche, Automationen, Diagnose und Supportpfade;
- GrowCentral Nexus UI;
- Mobile Nexus Clients;
- Cloud V6 und signierten APT-Pfad.

## Distribution

Der Deploy-Workflow veröffentlicht zusätzlich:

- `135ercloud-server-install.sh` – Cloud-/Server-Installer V6;
- `setup-135ercloud-apt-repo.sh` – signierter APT-Bootstrap;
- `RELEASE_STATE.md` – kanonischer Release-Stand;
- `SHA256SUMS.txt` – Prüfsummen der veröffentlichten Dateien;
- `release-state.txt` – maschinenlesbare Veröffentlichungsinformationen.

APT Repository: `https://repo.dezender.de/apt`

## Mobile

Mobile bleibt ein WebGUI-Client und ersetzt den Raspberry Pi nicht.

- Android: `GrowCentral-Nexus-Android-APK`
- iOS: `GrowCentral-Nexus-iOS-Sideload-IPA`
- Remote-Ziele müssen HTTPS verwenden.
- Die iOS-IPA wird ohne persönliche Apple-Signatur erzeugt und beim Sideloading für das konkrete Zielgerät signiert.

## Design

Die Website folgt verbindlich dem **GrowCentral Nexus UI**. Logo und Branding bleiben unverändert. Panelstruktur, Farben, Statussemantik, Typografie und responsive Regeln werden mit Pi-GUI, Kiosk, Mobile und Repo-Präsentation geteilt.

Designsystem: [`../docs/DESIGN_SYSTEM_NEXUS.md`](../docs/DESIGN_SYSTEM_NEXUS.md)

## Sicherheit

Die öffentliche Website bleibt read-only und enthält:

- keine lokalen Geräte-Credentials;
- keine Pi-Passwörter;
- keine direkten LAN-Steuerendpunkte;
- keine Smart-Home-Tokens.

## Branding und GUI-Vorschau

Branding:

- `assets/brand/135er-grow-central-lockup-v0.9.png`
- `assets/brand/135er-grow-central-logo.png`
- `assets/brand/135er-grow-central-mark.png`

GUI-Familie:

- `assets/gui/local-desktop-v0.9.png`
- `assets/gui/local-tablet-v0.9.png`
- `assets/gui/local-mobile-v0.9.png`
- `assets/gui/cloud-desktop-v0.9.png`

Aktuelle Vorschaubilder müssen Nexus UI zeigen. Veraltete Screenshots werden ersetzt oder als historisch markiert.

## Produktions-Deployment

Plesk-Webroot der Grow-Central-Seite:

```text
/var/www/vhosts/dezender.de/httpdocs/GC/
```

`.github/workflows/deploy-website-sftp.yml` veröffentlicht Änderungen an `website/**` und den kanonischen Server-/APT-Skripten automatisch nach:

```text
https://dezender.de/GC/
```

## Lokale Vorschau

```bash
cd website
python3 -m http.server 8000
```
