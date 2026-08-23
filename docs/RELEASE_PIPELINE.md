# Release-Pipeline – 135er-Grow Central

**Stand:** 2026-08-23  
**Kanonische Quelle:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

## Grundsatz

Es wird strikt zwischen vier Zuständen unterschieden:

1. **Repository-Stand** – aktueller `master`.
2. **Build/Artefakt** – durch GitHub Actions erzeugtes Paket.
3. **Hardware-Testkandidat** – Build, der als nächstes real geprüft werden soll.
4. **Hardwarevalidierte Basis** – Kandidat, der den realen Zieltest bestanden hat.

Eine Commit-, Run- oder Buildnummer ist deshalb nicht automatisch hardwarevalidiert.

## Aktueller Stand

- Version: **alpha-0.7.5**
- aktueller Master-Anker: **`e339602`**
- Build 117: vorheriger erfolgreicher Hardwaretest, inzwischen überholt
- nächster Raspberry-Pi-Testkandidat: **Build 118**
- Kandidaten-Tag: **`pi-universal-alpha-0.7.5-118`**
- Build 118: **CANDIDATE**, noch nicht `VALIDATED`
- Stable: noch nicht freigegeben

## Inhalt des konsolidierten Kandidaten

Build 118 basiert auf dem zusammengeführten aktuellen Stand einschließlich:

- aktueller GUI-/Netzwerk-/First-Boot-/Persistenzpfade;
- FRITZ! Smart Home und Tapo;
- Logitech C920/UVC;
- firmware-/modell-/USB-ID-bewusster Kamera-LED-Fähigkeitserkennung;
- bedingter V4L2-/Logitech-LED-Steuerung und Tests;
- Elecrow 7-Zoll Touch-Kiosk samt systemd-Service;
- Räume/Grow/Pflanzen/Automation;
- Energie-/Kostenlogik;
- GrowCentral Nexus UI;
- Mobile Nexus Clients;
- Cloud V6 und signiertem APT-Pfad.

## Verbindliche Release-Gates

1. Quellstand konsistent auf `master` zusammenführen.
2. Python-, Security-, Integrations- und Release-Guards ausführen.
3. Pi-Image exakt aus dem vorgesehenen Kandidatenstand verwenden.
4. Boot und Reboot auf realer Raspberry-Pi-Hardware prüfen.
5. First Boot, Setup-AP, LAN/WLAN, GUI und Persistenz prüfen.
6. C920 einschließlich LED-Fähigkeitserkennung/Steuerung auf realer Hardware prüfen.
7. Bei betroffenen Änderungen FRITZ!, Tapo, Mars Hydro und Elecrow-Kiosk prüfen.
8. Bei Fehlern Support-Paket erzeugen und auswerten.
9. Kandidaten erst nach erfolgreichem Realtest als `VALIDATED` kennzeichnen.
10. README, Website, Mobile-/Cloud-/APT-Doku und Downloads synchronisieren.

## Build-118-Regel

Build 118 wird nicht durch einen rein dokumentarischen Folgecommit künstlich ersetzt. Ein neuer Pi-Build >118 wird erst erzeugt, wenn sich der tatsächlich im Image enthaltene Laufzeitstand ändert oder Build 118 im Hardwaretest einen Fix erfordert. So bleibt der Hardwaretest reproduzierbar auf genau dem vorgesehenen Kandidaten.

## Distribution

### Raspberry Pi

Workflow: `.github/workflows/build-pi3-image.yml`

- Ziel: Raspberry Pi 3B+ / kompatible 64-bit Plattformbasis
- BUILD-Metadaten stammen aus GitHub Actions
- aktueller Testkandidat: Build 118
- Tag: `pi-universal-alpha-0.7.5-118`

### Mobile

Workflow: `.github/workflows/mobile-build.yml`

- Android: `GrowCentral-Nexus-Android-APK`
- iOS: `GrowCentral-Nexus-iOS-Sideload-IPA`
- iOS wird als unsigned Device-IPA erzeugt und erst beim Sideloading für das konkrete Gerät signiert
- Mobile bleibt WebGUI-Client; der Pi bleibt Geräteautorität
- lokale HTTP-Ziele: `.local` und private Netze
- Remote: HTTPS erforderlich

### Cloud / Server

Kanonische Installer:

- `scripts/install-135ercloud-v6.sh`
- `scripts/setup-135ercloud-apt-repo-v1.sh`

Die Website-Pipeline kopiert diese bei jedem Release-Abgleich erneut in den öffentlichen Webroot und veröffentlicht zusätzlich Release-Metadaten/Prüfsummen.

### APT

- Repository: `https://repo.dezender.de/apt`
- dedizierter `Signed-By`-Keyring
- alte Grow-Central-Quellen werden vor der kanonischen Einrichtung bereinigt
- APT-/Cloud-Installer bleiben inhaltlich an denselben Release-State gekoppelt

### Website

`dezender.de` ist eine öffentliche read-only Project Console im GrowCentral Nexus UI. Sie zeigt Kandidaten- und Validierungsstatus, darf aber keinen Testkandidaten als hardwarevalidiert ausgeben.

## Historische Dokumente

Dateien wie `BUILD_71_CHECKPOINT.md`, `BUILD_72_MOBILE_V0.1.md` und Build-85-spezifische Testnotizen bleiben als historische Nachweise erhalten. Sie definieren **nicht** mehr den aktuellen Release-Stand. Der aktuelle Status steht ausschließlich in `RELEASE_STATE.md`, dieser Pipeline und den darauf verweisenden Oberflächen.

## Release-Regel

Ein Paket gilt nur dann als **veröffentlicht/validiert**, wenn Quellstand, Artefakt, Prüfsummen und reale Zieltests eindeutig zueinander gehören. `CANDIDATE` und `VALIDATED` dürfen nicht synonym verwendet werden.
