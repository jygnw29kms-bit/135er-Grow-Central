<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · GrowCentral Nexus UI" width="100%"></p>

<p align="center">
  <a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="RELEASE_STATE.md"><strong>Release State</strong></a> · <a href="docs/README.md">Docs</a> · <a href="docs/RELEASE_PIPELINE.md">Pipeline</a> · <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.5-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Pi Candidate" src="https://img.shields.io/badge/Pi%20candidate-Build%20118-ffb52b?style=flat-square&labelColor=061015">
  <img alt="Runtime anchor" src="https://img.shields.io/badge/runtime-e339602-35e8da?style=flat-square&labelColor=061015">
  <img alt="Design" src="https://img.shields.io/badge/UI-GrowCentral%20Nexus-2ae5ff?style=flat-square&labelColor=061015">
</p>

<p align="center"><code>LOCAL-FIRST</code> · <code>RASPBERRY PI</code> · <code>MOBILE</code> · <code>FRITZ! SMART HOME</code> · <code>TAPO</code> · <code>C920/UVC</code> · <code>MARS HYDRO</code> · <code>SIGNED APT</code></p>

> [!IMPORTANT]
> **Kanonischer Stand:** `alpha-0.7.5`; Branch `master`; Build-118-Runtime-/Image-Anker `e339602`; nächster Raspberry-Pi-Hardwaretest **Build 118**; Kandidaten-Tag `pi-universal-alpha-0.7.5-118`. Build 117 war erfolgreich getestet, ist durch den zusammengeführten e339-Laufzeitstand aber überholt. **Build 118 bleibt CANDIDATE, bis der reale Hardwaretest bestanden ist.** Nach `e339602` enthält `master` zusätzliche Doku-, Mobile-, Design-, Packaging- und Publishing-Commits, ohne den vorgesehenen Pi-Laufzeitkandidaten künstlich zu Build 119 zu machen. Maßgeblich ist [`RELEASE_STATE.md`](RELEASE_STATE.md).

## Deutsch

**135er-Grow Central** ist eine local-first Steuer-, Überwachungs- und Automationsplattform für Raspberry Pi. Der Pi bleibt die autoritative lokale Instanz für GUI, Gerätepolicy, Smart Home, Kamera, Räume/Grow, Automation, Diagnose und optionalen abgesicherten Remotezugriff.

### Aktueller Stand · 23.08.2026

| Bereich | Stand |
|---|---|
| Repository | Branch `master`; HEAD enthält Runtime + aktuelle Doku/Packaging |
| Runtime/Image-Anker | `e339602` für Build 118 |
| Version | `alpha-0.7.5` |
| vorheriger Teststand | Build 117 · erfolgreich getestet, jetzt überholt |
| nächster Pi-Test | **Build 118** · `pi-universal-alpha-0.7.5-118` · CANDIDATE |
| Stable | noch nicht freigegeben |
| Design | **GrowCentral Nexus UI** projektweit verbindlich |
| Mobile | Nexus Mobile 0.2.1 · Android APK + iOS Sideload IPA |
| Cloud | Server Installer V6 |
| APT | signiert · `https://repo.dezender.de/apt` |

### Build 118 · Pi-Runtime

Der e339-Laufzeitstand umfasst:

- aktuelle Local-First GUI, First Boot, Netzwerk- und Persistenzpfade;
- FRITZ! Smart Home und authentifiziertes lokales Tapo-Onboarding;
- Logitech C920/UVC mit Snapshot, MJPEG und dynamischen V4L2-Reglern;
- **firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung**;
- bedingte Logitech/V4L2-LED-Steuerung statt blindem Schreiben;
- automatisierte Tests für LED-Fähigkeit und Steuersemantik;
- Elecrow 7-Zoll Touch-Kiosk inklusive systemd-Service und gehärteten Rechten;
- Räume, Growtagebuch, Pflanzen, Automationen sowie System-/Supportpfade;
- Energie-/Kostenlogik mit erhaltener Gesamtenergie.

### Nach e339 auf `master` synchronisiert

- kanonischer Release State und Build-118-Release-Notes;
- GrowCentral Nexus UI als verbindliches Designsystem für Repo/Web/Mobile/Pi-Präsentation;
- Nexus Mobile 0.2.1 und erneuter Android-/iOS-Buildtrigger;
- dezender.de Project Console auf Build 118 CANDIDATE;
- Cloud-V6/APT-Paketworkflow mit SHA-256;
- Release-Consistency-Guard gegen widersprüchliche Buildangaben.

### Hardwaretest Build 118

Build 118 ist der nächste reale Testkandidat. Vor **VALIDATED** müssen mindestens Boot/Reboot, First Boot, LAN/WLAN/AP, GUI, Persistenz, C920 inklusive LED-Fähigkeiten und die jeweils betroffenen Geräte-/Displaypfade geprüft werden. Bei Abweichungen ist `Grow-Central-Support-latest.tar.gz` die bevorzugte Diagnosebasis.

### Zugriff

- First Boot: `http://10.42.0.1/`
- lokal nach Einrichtung: `http://135er-Grow-Central.local/`
- Port `8080`: Kompatibilitätspfad
- Remote: nur über einen abgesicherten HTTPS-/VPN-/Reverse-Proxy-Pfad

### Mobile Apps

`mobile/` ist ein Capacitor-WebGUI-Client und ersetzt den Raspberry Pi nicht.

- Version: `0.2.1`
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

Der Cloud/APT-Paketworkflow validiert die Shell-Syntax und erzeugt ein Release-Bundle mit Release-State und SHA-256-Summen. Der Website-Deploy veröffentlicht Cloud-/APT-Installer ebenfalls mit Prüfsummen.

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

[Release State](RELEASE_STATE.md) · [Build 118 Notes](docs/RELEASE_NOTES_BUILD_118.md) · [Docs Hub](docs/README.md) · [Release Pipeline](docs/RELEASE_PIPELINE.md) · [Design System](docs/DESIGN_SYSTEM_NEXUS.md) · [Hardware Testplan](docs/HARDWARE_TEST_PLAN.md) · [Security](SECURITY.md)

---

## English

**135er-Grow Central alpha-0.7.5** is a local-first Raspberry Pi control, monitoring and automation platform. The **Build 118 runtime/image anchor is `e339602`**; the `master` branch has since received documentation, Nexus Mobile 0.2.1, packaging and publishing commits that do not change the intended Pi runtime candidate. **Build 117 was successfully tested but is superseded; Build 118 (`pi-universal-alpha-0.7.5-118`) is the next hardware-test candidate and remains CANDIDATE until the real target test passes.**

The Build 118 runtime combines the current GUI/network/FRITZ/Tapo/C920 state, firmware/model/USB-ID-aware camera LED capability detection and guarded LED controls, Elecrow 7-inch kiosk support and Grow/room features. Mobile, Cloud/APT and public presentation are synchronized around that candidate without artificially incrementing the Pi build.

Mobile remains a WebGUI client. Android is delivered as an APK artifact; iOS is delivered as an unsigned sideload IPA that is signed for the target device during installation. Remote access requires HTTPS or another secured transport path.

Canonical references: [Release State](RELEASE_STATE.md) · [Build 118 Notes](docs/RELEASE_NOTES_BUILD_118.md) · [Documentation](docs/README.md) · [Release Pipeline](docs/RELEASE_PIPELINE.md) · [Nexus Design System](docs/DESIGN_SYSTEM_NEXUS.md).

## Interface family / Interface-Familie

<table>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-desktop-v0.9.png" alt="GrowCentral local desktop concept"><br><strong>Local Desktop</strong></td>
    <td width="50%"><img src="website/assets/gui/local-tablet-v0.9.png" alt="GrowCentral local tablet concept"><br><strong>Local Tablet / Kiosk</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-mobile-v0.9.png" alt="GrowCentral mobile concept"><br><strong>Mobile Client</strong></td>
    <td width="50%"><img src="website/assets/gui/cloud-desktop-v0.9.png" alt="GrowCentral cloud concept"><br><strong>Optional Server</strong></td>
  </tr>
</table>

> [!NOTE]
> Existing v0.9 preview files are retained as concept/legacy references until replaced by final Nexus screenshots. Preview telemetry is demo data unless explicitly marked as hardware-validated.

<p align="center"><img src="website/assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central · J.L." width="760"></p>
