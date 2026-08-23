# 135er-Grow Central Wiki

## alpha-0.7.5 · GrowCentral Nexus · Build 118 Candidate

**135er-Grow Central** ist eine local-first Raspberry-Pi-Plattform für Smart Home, Kamera, Grow-Räume, Automationen, Energieauswertung und optionalen abgesicherten Remotezugriff.

**Kanonischer Stand:**

- Version: `alpha-0.7.5`
- Master-Anker: `e339602`
- Build 117: vorheriger erfolgreicher Teststand, inzwischen überholt
- Build 118: **nächster Hardwaretest-Kandidat**
- Tag: `pi-universal-alpha-0.7.5-118`
- Status: `CANDIDATE`, noch nicht hardwarevalidiert
- Design: **GrowCentral Nexus UI**

> Aktuelle Release-Aussagen werden ausschließlich aus [`../RELEASE_STATE.md`](../RELEASE_STATE.md) abgeleitet. Historische Wiki-/Build-Seiten definieren nicht den heutigen Stand.

## Plattform

```text
Android / iOS / Desktop / Kiosk
             |
      GrowCentral Nexus UI
             |
     135er-Grow Central Local
          Raspberry Pi
    /        |        |       \
 FRITZ!    Tapo    C920/UVC   Mars Hydro
                    + LED     iConnect/BLE
             |
      optional HTTPS Server V6
```

## Build 118 enthält

- aktuelle First-Boot-/Netzwerk-/Persistenzpfade;
- FRITZ! Smart Home und Tapo;
- Logitech C920/UVC, Snapshot, MJPEG und V4L2;
- firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung;
- bedingte LED-Steuerung nur bei erkannter Unterstützung;
- Elecrow 7-Zoll Touch-Kiosk;
- Räume, Pflanzen, Growtagebuch und Automationen;
- Mobile Nexus Clients;
- Cloud V6 und signiertes APT-Repository.

## Distribution

- Pi: Build 118 / `pi-universal-alpha-0.7.5-118`
- Android: `GrowCentral-Nexus-Android-APK`
- iOS: `GrowCentral-Nexus-iOS-Sideload-IPA`
- Cloud: Server Installer V6
- APT: `https://repo.dezender.de/apt`
- Website: `https://dezender.de`

## Dokumentation

- [Release State](../RELEASE_STATE.md)
- [Project Status](../docs/PROJECT_STATUS.md)
- [Build 118 Release Notes](../docs/RELEASE_NOTES_BUILD_118.md)
- [Release Pipeline](../docs/RELEASE_PIPELINE.md)
- [Nexus Design System](../docs/DESIGN_SYSTEM_NEXUS.md)
- [Hardware Tests](../docs/HARDWARE_TEST_PLAN.md)
- [Security Model](../docs/SECURITY_AND_TRUST_MODEL.md)
- [Mobile](../mobile/README.md)
