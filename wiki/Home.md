# 135er GrowControl Wiki

**135er GrowControl** ist eine Local-First-Steuer- und Monitoring-Plattform auf Debian-/Ubuntu-Basis mit Raspberry Pi als lokaler Master-Instanz und optionalem Linux-VServer als Cloud-Erweiterung.

Die Wiki-Quelle wird im Haupt-Repository versioniert. Sie dient als verbindliche Wissensbasis für Installation, Betrieb, Sicherheit, Datenmodell, Sensorik, Historie, Zeitpläne, Automationen, GUI, DF100M-Integration und die Raspberry-Pi-Testimages.

## Sprache / Language

- [Deutsch](de/README.md)
- [English](en/README.md)

## Kernprinzipien

- Raspberry Pi bleibt lokale Master-Instanz.
- Cloud ist optional und darf den lokalen Betrieb nicht blockieren.
- Debian/Ubuntu/Raspberry Pi OS 64-bit sind die Zielplattformen.
- Remote Commands sind standardmäßig deaktiviert und benötigen doppelte Freigabe.
- Experimentelle DF100M-BLE-Schreibzugriffe bleiben deaktiviert, bis das Protokoll validiert ist.
- Benutzer, Rollen, Rechte, Sensoren, Historie, Zeitpläne, Automationen und Audit-Daten werden strukturiert gespeichert.
- GUI ist responsiv für Desktop, Notebook, Tablet/iPad und Smartphone.
- Test-Images werden reproduzierbar gebaut, per SHA256 abgesichert und nicht als große Binärdateien in der normalen Git-Historie abgelegt.

## Raspberry Pi 3B Test-Image

Für die ersten Hardwaretests existiert ein reproduzierbarer GitHub-Actions-Builder für Raspberry Pi 3B / 3B+ auf Raspberry Pi OS Lite 64-bit / Debian 13.

Temporäre Testdaten:

```text
Hostname: growcontrol-test
Username: test
Password: test
API/App token: test
Cloud token: test
Web UI: http://<PI-IP>:8080
```

DF100M-Schreibzugriffe, Remote Commands und Cloud bleiben standardmäßig deaktiviert.

- [Deutsch: Raspberry Pi 3B Test-Image](de/RASPBERRY_PI_3B_TEST_IMAGE.md)
- [English: Raspberry Pi 3B Test Image](en/RASPBERRY_PI_3B_TEST_IMAGE.md)

## Projektstatus

Version: **v0.5 Full Platform Baseline**

Aktueller Fokus: erste reale Raspberry-Pi-/DF100M-Hardwaretests auf Basis der konsolidierten Local/Cloud-/BLE-Plattform. Der korrigierte v2-Image-Builder erweitert das Basisimage sowie Root-Partition und Dateisystem vor der Installation und schließt temporäre Builddateien aus der Projektkopie aus.
