<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · GrowCentral Nexus UI" width="100%"></p>

<p align="center">
  <a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="RELEASE_STATE.md"><strong>Release State</strong></a> · <a href="docs/README.md">Docs</a> · <a href="docs/RELEASE_PIPELINE.md">Pipeline</a> · <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.5-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Pi Candidate" src="https://img.shields.io/badge/Pi%20candidate-Build%20118-ffb52b?style=flat-square&labelColor=061015">
  <img alt="Master" src="https://img.shields.io/badge/master-e339602-35e8da?style=flat-square&labelColor=061015">
  <img alt="Design" src="https://img.shields.io/badge/UI-GrowCentral%20Nexus-2ae5ff?style=flat-square&labelColor=061015">
</p>

<p align="center"><code>LOCAL-FIRST</code> · <code>RASPBERRY PI</code> · <code>MOBILE</code> · <code>FRITZ! SMART HOME</code> · <code>TAPO</code> · <code>C920/UVC</code> · <code>MARS HYDRO</code> · <code>SIGNED APT</code></p>

> [!IMPORTANT]
> **Kanonischer Stand:** `alpha-0.7.5`, Master-Anker `e339602`, nächster Raspberry-Pi-Hardwaretest **Build 118**, Kandidaten-Tag `pi-universal-alpha-0.7.5-118`. Build 117 war erfolgreich getestet, ist durch den zusammengeführten e339-Stand aber überholt. **Build 118 ist Kandidat, noch nicht hardwarevalidiert.** Maßgeblich ist [`RELEASE_STATE.md`](RELEASE_STATE.md).

## Deutsch

**135er-Grow Central** ist eine local-first Steuer-, Überwachungs- und Automationsplattform für Raspberry Pi. Der Pi bleibt die autoritative lokale Instanz für GUI, Gerätepolicy, Smart Home, Kamera, Räume/Grow, Automation, Diagnose und optionalen abgesicherten Remotezugriff.

### Aktueller Stand · 23.08.2026

| Bereich | Stand |
|---|---|
| Repository | `master` · Anker `e339602` |
| Version | `alpha-0.7.5` |
| vorheriger Teststand | Build 117 · erfolgreich getestet, jetzt überholt |
| nächster Pi-Test | **Build 118** · `pi-universal-alpha-0.7.5-118` |
| Stable | noch nicht freigegeben |
| Design | **GrowCentral Nexus UI** projektweit verbindlich |
| Mobile | Nexus WebGUI Client · Android APK + iOS Sideload IPA |
| Cloud | Server Installer V6 |
| APT | signiert · `https://repo.dezender.de/apt` |

### In Build 118 zusammengeführt

- aktuelle Local-First GUI, First Boot, Netzwerk- und Persistenzpfade;
- FRITZ! Smart Home und authentifiziertes lokales Tapo-Onboarding;
- Logitech C920/UVC mit Snapshot, MJPEG und dynamischen V4L2-Reglern;
- **firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung**;
- bedingte Logitech/V4L2-LED-Steuerung statt blindem Schreiben;
- automatisierte Tests für LED-Fähigkeit und Steuersemantik;
- Elecrow 7-Zoll Touch-Kiosk inklusive systemd-Service und gehärteten Rechten;
- Räume, Growtagebuch, Pflanzen, Automationen und System-/Supportansichten;
- Energie-/Kostenlogik mit erhaltener Gesamtenergie;
- GrowCentral Nexus UI als gemeinsame Designsprache;
- Mobile Nexus Clients, Cloud V6 und signierter APT-Pfad.

### Hardwaretest Build 118

Build 118 ist der nächste reale Testkandidat. Vor einer Kennzeichnung als **VALIDATED** müssen mindestens Boot/Reboot, First Boot, LAN/WLAN/AP, GUI, Persistenz, C920 inkl. LED-Fähigkeiten und die jeweils betroffenen Gerätepfade geprüft werden. Bei Abweichungen ist `Grow-Central-Support-latest.tar.gz` die bevorzugte Diagnosebasis.

### Zugriff

- First Boot: `http://10.42.0.1/`
- lokal nach Einrichtung: `http://135er-Grow-Central.local/`
- Port `8080`: Kompatibilitätspfad
- Remote: nur über einen abgesicherten HTTPS-/VPN-/Reverse-Proxy-Pfad

### Mobile Apps

`mobile/` ist ein Capacitor-WebGUI-Client und ersetzt den Raspberry Pi nicht.

- Android: GitHub-Actions-Artefakt `GrowCentral-Nexus-Android-APK`
- iOS: `GrowCentral-Nexus-iOS-Sideload-IPA`
- iOS-IPA wird ohne persönliche Apple-Signatur gebaut und beim Sideloading gerätebezogen signiert.
- keine FRITZ!-, Tapo- oder sonstigen Geräte-Credentials im Mobile-Paket.

### Cloud / APT

Kanonische Serverpfade:

- `scripts/install-135ercloud-v6.sh`
- `scripts/setup-135ercloud-apt-repo-v1.sh`
- `https://repo.dezender.de/apt`
- öffentliche Project Console: `https://dezender.de`

APT nutzt einen dedizierten `Signed-By`-Keyring und bereinigt alte widersprüchliche Grow-Central-Quellen vor dem Einrichten der kanonischen Quelle.

### Design

Logo und Branding bleiben unverändert. Alle Pi-, Web-, Mobile-, Repo-, Boot-, Kiosk- und Release-Oberflächen folgen dem **GrowCentral Nexus UI**. Verbindliche Tokens und Komponentenregeln stehen in [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md).

### Sicherheit

- deny-by-default für Schreibpfade;
- authentifizierte GUI-Sitzung oder explizites API-Token für Writes;
- Geräte müssen bekannt, freigegeben und beschreibbar sein;
- Integrationspasswörter werden nicht an Browser-APIs zurückgegeben;
- öffentliche Website besitzt keine lokalen Steuerendpunkte;
- Mobile Remote-Ziele benötigen HTTPS.

### Dokumentation

[Release State](RELEASE_STATE.md) · [Docs Hub](docs/README.md) · [Release Pipeline](docs/RELEASE_PIPELINE.md) · [Design System](docs/DESIGN_SYSTEM_NEXUS.md) · [Hardware Testplan](docs/HARDWARE_TEST_PLAN.md) · [Security](SECURITY.md)

---

## English

**135er-Grow Central alpha-0.7.5** is a local-first Raspberry Pi control, monitoring and automation platform. The current consolidated master anchor is `e339602`. **Build 117 was successfully tested but is now superseded; Build 118 (`pi-universal-alpha-0.7.5-118`) is the next hardware-test candidate and must not be called hardware-validated before the real target test passes.**

Build 118 combines the current GUI/network/FRITZ/Tapo/C920 state, firmware/model/USB-ID-aware camera LED capability detection and guarded LED controls, Elecrow 7-inch kiosk support, Grow/room features, Nexus UI, Mobile clients, Cloud V6 and the signed APT path.

Mobile remains a WebGUI client. Android is delivered as an APK artifact; iOS is delivered as an unsigned sideload IPA that is signed for the target device during installation. Remote access requires HTTPS or another secured transport path.

Canonical references: [Release State](RELEASE_STATE.md) · [Documentation](docs/README.md) · [Release Pipeline](docs/RELEASE_PIPELINE.md) · [Nexus Design System](docs/DESIGN_SYSTEM_NEXUS.md).

## Interface family / Interface-Familie

<table>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-desktop-v0.9.png" alt="GrowCentral Nexus local desktop"><br><strong>Local Desktop</strong></td>
    <td width="50%"><img src="website/assets/gui/local-tablet-v0.9.png" alt="GrowCentral Nexus local tablet"><br><strong>Local Tablet / Kiosk</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-mobile-v0.9.png" alt="GrowCentral Nexus mobile"><br><strong>Mobile Client</strong></td>
    <td width="50%"><img src="website/assets/gui/cloud-desktop-v0.9.png" alt="GrowCentral Nexus cloud"><br><strong>Optional Server</strong></td>
  </tr>
</table>

> [!NOTE]
> Preview telemetry is concept/demo data unless explicitly marked as hardware-validated.

<p align="center"><img src="website/assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central · J.L." width="760"></p>
