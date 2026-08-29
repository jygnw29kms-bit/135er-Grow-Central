# Universelles Raspberry-Pi-Image mit Hardwareprofilen

> Der Dateiname dieses Dokuments ist historisch. Das aktuelle GrowCentral-Image ist **kein Pi-3-only-Image**, sondern ein Universal-Image.

## Unterstützte Hardware

- Raspberry Pi 3B / 3B+ → **Legacy/Lite**
- Raspberry Pi 4B / 400 / Compute Module 4 → **Full Support Standard**
- Raspberry Pi 5 / Compute Module 5 → **Full Support Performance**

Pi 3 bleibt unterstützt, erhält aber konservative Ressourcenlimits. Neue Full-Support-Funktionen orientieren sich an Pi 4/5.

## Zentrale Runtime-Erkennung

Das Modell wird aus `/proc/device-tree/model` gelesen. Die verbindliche Klassifikation liegt in `shared/hardware_profile.py` und wird von Diagnose und hardwareabhängigen Runtime-Pfaden verwendet.

Legacy/Lite nutzt u. a. Kamera bis 1280×720, reduzierte FPS, reduzierte Kiosk-Effekte, kompakte Diagnosehistorie und konservative Worker. Pi 4/5 dürfen Full-Support-Profile bis 1920×1080 nutzen.

## Image-Strategie

Es bleibt bei **einem Universal-Image**. Separate Images werden erst eingeführt, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden.

## Basis

- Raspberry Pi OS Lite 64-bit / Debian 13 Trixie
- NetworkManager, systemd, Bluetooth/BlueZ, SSH, UFW
- GrowCentral Runtime in `/opt/135er-grow-central`
- First Boot über Setup-AP und Captive Portal
- lokale GUI über `http://135er-GrowCentral.local/`
- Diagnose mit Modell und Hardwareprofil

## First Boot

1. Universal-Image flashen.
2. `135er-GrowCentral-Setup-XXXX` verbinden.
3. `http://10.42.0.1/` öffnen.
4. Netzwerk sowie getrennte GUI- und System/SSH-Credentials konfigurieren.
5. Setup abschließen und rebooten.
6. `http://135er-GrowCentral.local/` oder die IP öffnen.
7. In der Diagnose kontrollieren, ob Modell und Supportklasse korrekt erkannt wurden.

Bei fehlgeschlagener WLAN-Verbindung wird der Setup-AP automatisch wiederhergestellt.

## Sicherheitsbaseline

- Root-SSH deaktiviert
- UFW aktiviert
- automatische Security-Updates
- DF100M-Schreibzugriffe standardmäßig aus
- Remote-Cloud-Befehle standardmäßig aus
- Cloud standardmäßig aus

## Validierung

Reale Hardwaretests werden nicht mehr pauschal für „Raspberry Pi“ geführt, sondern getrennt für:

- Legacy/Lite Pi 3B/3B+
- Full Support Pi 4/400
- Full Support Performance Pi 5

Ein Pi-3-spezifischer Legacy/Lite-Fehler blockiert nicht automatisch die Pi-4/5-Full-Support-Freigabe. Siehe [`../HARDWARE_TEST_PLAN.md`](../HARDWARE_TEST_PLAN.md) und [`../HARDWARE_SUPPORT_POLICY.md`](../HARDWARE_SUPPORT_POLICY.md).
