# Raspberry Pi 3B Test-Image

Dieses Dokument beschreibt das reproduzierbare Test-Image für **135er-Grow Central** auf Raspberry Pi 3B / 3B+.

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

Das aktuelle Repository wird nach `/opt/135er-grow-central` kopiert. Die Python-Abhängigkeiten werden in `/opt/135er-grow-central/.venv` installiert.

Der lokale Dienst startet automatisch über `135er-grow-central.service` und stellt die Web/API-Oberfläche auf Port `8080` bereit.

```text
http://<PI-IP>:8080
```

## Temporäre Test-Zugangsdaten

Nur für die ersten Hardwaretests:

```text
Hostname: grow-central-test
SSH-Benutzer: test
SSH-Passwort: test
API-/App-Token: test
Cloud-Token: test
```

Diese Daten sind absichtlich unsicher und müssen nach den Tests ersetzt werden.

## Sicherheitsstatus im Test-Image

- Root-SSH-Login deaktiviert
- Passwort-SSH für den temporären Benutzer `test` aktiviert
- UFW aktiviert
- eingehend erlaubt: TCP 22 und TCP 8080
- automatische Sicherheitsupdates aktiviert
- DF100M-Schreibzugriffe standardmäßig deaktiviert
- Remote-Cloud-Befehle standardmäßig deaktiviert
- Cloud standardmäßig deaktiviert

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

Der Build läuft reproduzierbar über GitHub Actions. Das offizielle Raspberry-Pi-OS-Image wird heruntergeladen und per fest hinterlegtem SHA256 geprüft. Danach wird das Root-Dateisystem erweitert, Grow Central eingebaut, das Image komprimiert und erneut mit SHA256 versehen.

Ausgaben:

```text
135er-Grow-Central_RPi3B_Test.img.xz
135er-Grow-Central_RPi3B_Test.img.xz.sha256
135er-Grow-Central_RPi3B_Test-CREDENTIALS.txt
135er_Grow_Central_RPi3B_Test-QEMU-Windows-Kit.zip
```

Das fertige Image wird als GitHub Actions Artefakt und als GitHub Prerelease vorgesehen. Große Binärimages werden bewusst nicht direkt in die normale Git-Historie eingecheckt.

## Test ohne Raspberry Pi unter Windows

Der Build erzeugt zusätzlich ein QEMU-Windows-Kit und prüft das ARM64-Image bereits automatisiert bis zum Mehrbenutzermodus. Für den lokalen Test werden das Image und das QEMU-Kit aus demselben Release heruntergeladen. Nach dem Entpacken liegen `.img.xz`, Kernel, Initramfs und Startskripte gemeinsam in einem Ordner. `start-qemu-windows.cmd` entpackt das Image und startet QEMU.

```text
Weboberfläche: http://localhost:8080
SSH: ssh -p 2222 test@localhost
Benutzer / Passwort: test / test
```

Damit werden ARM64-Boot, Linux, systemd, Netzwerk, SSH und die Grow-Central-Anwendung geprüft. Bluetooth, GPIO, Raspberry-Pi-Firmware und DF100M-Funkkommunikation können ohne echte Hardware nicht verifiziert werden.

## Bekannter Build-Verlauf

Der erste Builderlauf scheiterte beim Kopieren, weil die lokal heruntergeladene Basis-Image-Datei versehentlich mit in das Ziel-Dateisystem kopiert wurde und dessen freien Platz aufbrauchte.

Die Korrektur umfasst:

- Ausschluss von `base.img.xz`, `work.img` und Build-Ausgaben aus `rsync`
- Vergrößerung des Images vor der Installation
- Vergrößerung der Root-Partition und des ext4-Dateisystems
- separater v2-Workflow für den korrigierten Testbuild

## Erster Hardwaretest

1. `.img.xz` mit Raspberry Pi Imager oder einem kompatiblen Tool auf SD-Karte schreiben.
2. Raspberry Pi 3B per Ethernet ins lokale Netz hängen.
3. Pi booten lassen.
4. IP im Router/DHCP-Server ermitteln.
5. SSH testen: `ssh test@<PI-IP>`.
6. Webinterface öffnen: `http://<PI-IP>:8080`.
7. Service prüfen: `systemctl status 135er-grow-central`.
8. Bluetooth prüfen: `bluetoothctl show`.
9. Mars Legacy App vollständig schließen, bevor BLE-Tests gestartet werden.
10. DF100M zunächst nur entdecken, verbinden, Services/GATT prüfen und Notifications mitschneiden. Schreibzugriffe erst nach Protokollvalidierung aktivieren.
