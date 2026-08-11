# Raspberry Pi 3B Test-Image

Für die ersten Hardwaretests wird ein reproduzierbares Raspberry-Pi-3B/3B+-Image auf Basis von Raspberry Pi OS Lite 64-bit / Debian 13 gebaut.

## Vorinstalliert

- 135er-Grow Central unter `/opt/135er-grow-central`
- Python-Venv und Projektabhängigkeiten
- Bluetooth / BlueZ
- SSH
- UFW
- unattended-upgrades
- Web-Ersteinrichtung per temporärem WLAN-Zugangspunkt
- systemd-Start von `135er-grow-central.service` nach erfolgreicher Ersteinrichtung

Weboberfläche:

```text
http://<PI-IP>:8080
```

## Temporäre Zugangsdaten

```text
Hostname: grow-central-test
Benutzer: GrowCentral
Passwort: grow-central-test
API-/App-Token: test
Cloud-Token: test
```

**Nur für den Erststart.** Das Portal verlangt vor dem Start des Hauptsystems ein neues Passwort mit mindestens zwölf Zeichen.

## Erster Start

1. Mit `135er-GrowCentral-Setup-XXXX` verbinden; WLAN-Schlüssel: `grow-central-test`.
2. `https://10.42.0.1` öffnen und das lokale Zertifikat bestätigen.
3. Als `GrowCentral` mit `grow-central-test` anmelden.
4. Ziel-WLAN oder LAN, Hostname, Zeitzone und neues Passwort festlegen.
5. Nach erfolgreicher Prüfung beendet sich der Setup-Modus und Grow Central startet.

Schlägt die WLAN-Verbindung fehl, wird der Setup-Zugangspunkt automatisch wieder aktiviert.

## Sichere Test-Defaults

- DF100M-Schreibzugriffe: deaktiviert
- Remote Cloud Commands: deaktiviert
- Cloud: deaktiviert
- Root-SSH: deaktiviert
- Firewall: SSH (22/TCP), Grow Central (8080/TCP) sowie nur im Setup-Netz temporär HTTP/HTTPS (80/443)

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
2. Web-Ersteinrichtung abschließen.
3. IP ermitteln.
4. `ssh GrowCentral@<PI-IP>` testen.
5. `http://<PI-IP>:8080` öffnen.
6. `systemctl status 135er-grow-central` prüfen.
7. `bluetoothctl show` prüfen.
8. Mars Legacy App schließen.
9. DF100M entdecken, verbinden, GATT prüfen und Notifications erfassen.
10. Keine BLE-Schreibtests, bevor das Protokoll ausreichend validiert wurde.

Ausführliche technische Dokumentation: `docs/de/RASPBERRY_PI_3B_TEST_IMAGE.md`.
