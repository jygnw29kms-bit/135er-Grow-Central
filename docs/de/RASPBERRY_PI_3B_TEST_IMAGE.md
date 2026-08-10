# Raspberry Pi 3B Test-Image

Dieses Dokument beschreibt das reproduzierbare Test-Image fÃ¼r **135er-Grow Central** auf Raspberry Pi 3B / 3B+.

## Basis

- Raspberry Pi OS Lite 64-bit
- Debian 13 / Trixie
- Raspberry Pi 3B / 3B+
- systemd
- Python Virtual Environment
- Bluetooth / BlueZ
- SSH
- UFW
- unattended-upgrades

## Vorinstalliertes Projekt

Das aktuelle Repository wird nach `/opt/135er-grow-central` kopiert. Die Python-AbhÃ¤ngigkeiten werden in `/opt/135er-grow-central/.venv` installiert.

Der lokale Dienst startet automatisch Ã¼ber `135er-grow-central.service` und stellt die Web/API-OberflÃ¤che auf Port `8080` bereit.

```text
http://<PI-IP>:8080
```

## TemporÃ¤re Test-Zugangsdaten

Nur fÃ¼r die ersten Hardwaretests:

```text
Hostname: grow-central-test
SSH-Benutzer: GrowCentral
SSH-Passwort: test
API-/App-Token: test
Cloud-Token: test
```

Diese Daten sind absichtlich unsicher und mÃ¼ssen nach den Tests ersetzt werden.

## Sicherheitsstatus im Test-Image

- Root-SSH-Login deaktiviert
- Passwort-SSH fÃ¼r den festen Headless-Benutzer `GrowCentral` aktiviert
- Locale `de_DE.UTF-8`, Zeitzone `Europe/Berlin` und Tastaturbelegung `de(nodeadkeys)` vorkonfiguriert
- interaktive First-Boot-Abfragen fÃ¼r Benutzer und Tastatur deaktiviert
- UFW aktiviert
- eingehend erlaubt: TCP 22 und TCP 8080
- automatische Sicherheitsupdates aktiviert
- DF100M-Schreibzugriffe standardmÃ¤ÃŸig deaktiviert
- Remote-Cloud-Befehle standardmÃ¤ÃŸig deaktiviert
- Cloud standardmÃ¤ÃŸig deaktiviert

## DF100M-Testkonfiguration

```text
DF100M_NAME_HINT=MZ_MZF002
DF100M_WRITE_UUID=f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
DF100M_NOTIFY_UUID=83677baa-3eb8-4866-b6b6-96e5ed5cc48d
DF100M_SPEED_MODE=byte
DF100M_ALLOW_WRITES=false
```

Die UUIDs und Payload-Modi sind Reverse-Engineering-Kandidaten und noch keine validierte Herstellerdokumentation.

## Image-Build

Der Build lÃ¤uft reproduzierbar Ã¼ber GitHub Actions. Das offizielle Raspberry-Pi-OS-Image wird heruntergeladen und per fest hinterlegtem SHA256 geprÃ¼ft. Danach wird das Root-Dateisystem erweitert, Grow Central eingebaut, das Image komprimiert und erneut mit SHA256 versehen.

Ausgaben:

```text
135er-Grow-Central_RPi3B_Test.img.xz
135er-Grow-Central_RPi3B_Test.img.xz.sha256
135er-Grow-Central_RPi3B_Test-CREDENTIALS.txt
```

Das fertige Image wird als GitHub Actions Artefakt und als GitHub Prerelease vorgesehen. GroÃŸe BinÃ¤rimages werden bewusst nicht direkt in die normale Git-Historie eingecheckt.

## Test ohne Raspberry Pi unter Windows

FÃ¼r QEMU wird bewusst ein getrenntes Debian-13-ARM64-Image gebaut. Der Raspberry-Pi-Kernel bleibt auf reale Pi-Hardware optimiert, wÃ¤hrend das virtuelle Image einen VirtIO-fÃ¤higen Kernel fÃ¼r Festplatte und Netzwerk verwendet. Der QEMU-Workflow startet das fertige System und prÃ¼ft `/api/health`, bevor `135er_Grow_Central_QEMU_ARM64-Windows.zip` verÃ¶ffentlicht wird. Nach dem Entpacken startet `start-qemu-arm64-windows.cmd` die virtuelle Maschine.

```text
WeboberflÃ¤che: http://localhost:8080
SSH: ssh -p 2222 test@localhost
Benutzer / Passwort: test / test
```

Damit werden ARM64-Boot, Linux, systemd, Netzwerk, SSH und die Grow-Central-Anwendung geprÃ¼ft. Bluetooth, GPIO, Raspberry-Pi-Firmware und DF100M-Funkkommunikation kÃ¶nnen ohne echte Hardware nicht verifiziert werden.

## Bekannter Build-Verlauf

Der erste Builderlauf scheiterte beim Kopieren, weil die lokal heruntergeladene Basis-Image-Datei versehentlich mit in das Ziel-Dateisystem kopiert wurde und dessen freien Platz aufbrauchte.

Die Korrektur umfasst:

- Ausschluss von `base.img.xz`, `work.img` und Build-Ausgaben aus `rsync`
- VergrÃ¶ÃŸerung des Images vor der Installation
- VergrÃ¶ÃŸerung der Root-Partition und des ext4-Dateisystems
- separater v2-Workflow fÃ¼r den korrigierten Testbuild

## Erster Hardwaretest

1. `.img.xz` mit Raspberry Pi Imager oder einem kompatiblen Tool auf SD-Karte schreiben.
2. Raspberry Pi 3B per Ethernet ins lokale Netz hÃ¤ngen.
3. Pi booten lassen.
4. IP im Router/DHCP-Server ermitteln.
5. SSH testen: `ssh GrowCentral@<PI-IP>`.
6. Webinterface Ã¶ffnen: `http://<PI-IP>:8080`.
7. Service prÃ¼fen: `systemctl status 135er-grow-central`.
8. Bluetooth prÃ¼fen: `bluetoothctl show`.
9. Mars Legacy App vollstÃ¤ndig schlieÃŸen, bevor BLE-Tests gestartet werden.
10. DF100M zunÃ¤chst nur entdecken, verbinden, Services/GATT prÃ¼fen und Notifications mitschneiden. Schreibzugriffe erst nach Protokollvalidierung aktivieren.
