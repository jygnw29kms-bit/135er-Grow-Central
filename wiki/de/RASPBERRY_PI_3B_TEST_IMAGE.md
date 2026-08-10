# Raspberry Pi 3B Test-Image

Für die ersten Hardwaretests wird ein reproduzierbares Raspberry-Pi-3B/3B+-Image auf Basis von Raspberry Pi OS Lite 64-bit / Debian 13 gebaut.

## Vorinstalliert

- 135er-Grow Central unter `/opt/135er-grow-central`
- Python-Venv und Projektabhängigkeiten
- Bluetooth / BlueZ
- SSH
- UFW
- unattended-upgrades
- systemd-Autostart von `135er-grow-central.service`

Weboberfläche:

```text
http://<PI-IP>:8080
```

## Temporäre Zugangsdaten

```text
Hostname: grow-central-test
Benutzer: test
Passwort: test
API-/App-Token: test
Cloud-Token: test
```

**Nur für Tests.** Nach Abschluss der Hardwaretests müssen diese Zugangsdaten ersetzt werden.

## Sichere Test-Defaults

- DF100M-Schreibzugriffe: deaktiviert
- Remote Cloud Commands: deaktiviert
- Cloud: deaktiviert
- Root-SSH: deaktiviert
- Firewall: nur SSH (22/TCP) und Grow Central (8080/TCP)

## Build und Veröffentlichung

GitHub Actions lädt das offizielle Raspberry-Pi-OS-Image, prüft den fest hinterlegten SHA256, erweitert Root-Partition/Dateisystem, installiert Grow Central und erzeugt:

```text
135er-Grow-Central_RPi3B_Test.img.xz
135er-Grow-Central_RPi3B_Test.img.xz.sha256
135er-Grow-Central_RPi3B_Test-CREDENTIALS.txt
```

Das Image wird als Actions-Artefakt bzw. Prerelease veröffentlicht und nicht als große Binärdatei in die normale Git-Historie geschrieben.

## Build-Korrektur

Der aktuelle Builder schließt Build-Dateien aus und vergrößert Image, Root-Partition und ext4-Dateisystem vor der Installation. Der Build läuft nativ auf ARM64.

## Testablauf

1. Image auf SD-Karte flashen.
2. Pi per Ethernet verbinden und booten.
3. IP ermitteln.
4. `ssh test@<PI-IP>` testen.
5. `http://<PI-IP>:8080` öffnen.
6. `systemctl status 135er-grow-central` prüfen.
7. `bluetoothctl show` prüfen.
8. Mars Legacy App schließen.
9. DF100M entdecken, verbinden, GATT prüfen und Notifications erfassen.
10. Keine BLE-Schreibtests, bevor das Protokoll ausreichend validiert wurde.

Ausführliche technische Dokumentation: `docs/de/RASPBERRY_PI_3B_TEST_IMAGE.md`.
