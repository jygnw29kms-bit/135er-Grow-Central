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

Der lokale Dienst startet automatisch über `135er-grow-central.service`. Die einfache Adresse wird über einen abgesicherten systemd-Socket auf Port `80` bereitgestellt; die Anwendung bleibt intern und zur Kompatibilität auf Port `8080` erreichbar.

```text
http://<PI-IP>/
```

## Temporäre Test-Zugangsdaten

Nur für die ersten Hardwaretests:

```text
Hostname: 135er-grow-central
LAN-Adresse: http://135er-grow-central.local/
SSH-Benutzer: GrowCentral
SSH-Passwort: grow-central-test
API-/App-Token: test
Cloud-Token: test
```

Die normale Haupt-GUI ist ab dem ersten Boot verfügbar. Ihre System-Seite verlangt neue System- und GUI-Passwörter mit mindestens zwölf Zeichen.

## Web-Ersteinrichtung

1. Nach dem ersten Start das WLAN `135er-GrowCentral-Setup-XXXX` auswählen. Die vier Schlusszeichen stammen aus der WLAN-MAC-Adresse des Pi.
2. Mit dem temporären WLAN-Schlüssel `grow-central-test` verbinden.
3. `http://10.42.0.1/` öffnen.
4. Mit `GrowCentral` / `grow-central-test` an der Haupt-GUI anmelden und **System** öffnen.
5. Ziel-WLAN oder LAN, Zeitzone sowie neue System- und GUI-Zugangsdaten eintragen. Beim aktiven Pi-3B-AP die SSID nötigenfalls manuell eingeben.
6. Nach erfolgreicher Netzwerk-, GUI- und mDNS-Prüfung wird der Setup-Zugangspunkt deaktiviert; die feste Adresse ist `http://135er-Grow-Central.local/`. Port `8080` bleibt kompatibel.

Bei Problemen immer die unter **System** erzeugbare Datei `Grow-Central-Support-latest.tar.gz` mitsenden. Das Image erstellt sie bei First-Boot- und Dienstfehlern auch automatisch.

Unter **System** zeigt die GUI nicht nur die Softwareversion und Image-Buildnummer, sondern liest das reale Raspberry-Pi-Modell aus `/proc/device-tree/model`. Das gleiche Image kann dadurch bei Hardwaretests einen Pi 3B/3B+ und einen Pi 4 korrekt unterscheiden.

Der Kamerabereich bietet neben Snapshots ein bewusst manuell gestartetes C920-MJPEG-Livebild mit 640×480 und 10 Bildern pro Sekunde. Es läuft maximal ein Stream gleichzeitig und wird beim Verlassen des Kamerabereichs beendet.

Bei einer fehlgeschlagenen WLAN-Verbindung wird der Setup-Zugangspunkt automatisch wiederhergestellt. Ziel-WLAN-Passwörter werden nur in der rootgeschützten NetworkManager-Konfiguration gespeichert und nicht protokolliert.

Das Setup-Netz arbeitet im Dual-Stack-Betrieb. Der zuverlässige IPv4-Hauptweg
verwendet auf dem Raspberry Pi fest `10.42.0.1/24`; NetworkManager vergibt per
DHCP Adressen von `10.42.0.10` bis `10.42.0.250`. Das Portal startet erst, wenn
der DHCP-Listener nachweislich aktiv ist. IPv6 wird parallel im Shared Mode bereitgestellt. Das
AP-Profil wird bei jedem Start vollständig erneut angewendet, damit auch ein
zuvor unterbrochener erster Boot automatisch repariert wird. Die anschließend
konfigurierte WLAN-Verbindung verwendet IPv4 und IPv6 automatisch, sofern das
Zielnetz beide Protokolle anbietet.

## Sicherheitsstatus im Test-Image

- Root-SSH-Login deaktiviert
- Passwort-SSH für den festen Headless-Benutzer `GrowCentral` aktiviert
- Locale `de_DE.UTF-8`, Zeitzone `Europe/Berlin` und Tastaturbelegung `de(nodeadkeys)` vorkonfiguriert
- interaktive First-Boot-Abfragen für Benutzer und Tastatur deaktiviert
- UFW aktiviert
- eingehend erlaubt: TCP 22, TCP 80 für die einfache GUI-Adresse, TCP 8080 als Kompatibilitätsadresse und UDP 5353 für mDNS; während der Ersteinrichtung zusätzlich DHCP 67/UDP und DNS 53/TCP+UDP auf dem Setup-WLAN `wlan0`
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
```

Das fertige Image wird als GitHub Actions Artefakt und als GitHub Prerelease vorgesehen. Große Binärimages werden bewusst nicht direkt in die normale Git-Historie eingecheckt.

## Bekannter Build-Verlauf

Der erste Builderlauf scheiterte beim Kopieren, weil die lokal heruntergeladene Basis-Image-Datei versehentlich mit in das Ziel-Dateisystem kopiert wurde und dessen freien Platz aufbrauchte.

Die Korrektur umfasst:

- Ausschluss von `base.img.xz`, `work.img` und Build-Ausgaben aus `rsync`
- Vergrößerung des Images vor der Installation
- Vergrößerung der Root-Partition und des ext4-Dateisystems
- nativer ARM64-Workflow für den reproduzierbaren Testbuild

## Erster Hardwaretest

1. `.img.xz` mit Raspberry Pi Imager oder einem kompatiblen Tool auf SD-Karte schreiben.
2. Pi booten und die oben beschriebene Web-Ersteinrichtung abschließen.
3. Die neue IP im Portal/Router ermitteln.
4. SSH testen: `ssh GrowCentral@<PI-IP>`.
5. Webinterface öffnen: `http://<PI-IP>/`.
7. Service prüfen: `systemctl status 135er-grow-central`.
8. Bluetooth prüfen: `bluetoothctl show`.
9. Mars Legacy App vollständig schließen, bevor BLE-Tests gestartet werden.
10. DF100M zunächst nur entdecken, verbinden, Services/GATT prüfen und Notifications mitschneiden. Schreibzugriffe erst nach Protokollvalidierung aktivieren.
