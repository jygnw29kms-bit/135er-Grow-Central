# 135er GrowControl Wiki

**135er GrowControl** ist eine Local-First-Steuer- und Monitoring-Plattform auf Debian-/Ubuntu-Basis mit Raspberry Pi als lokaler Master-Instanz und optionalem Linux-VServer als Cloud-Erweiterung.

Die Wiki-Quelle wird im Haupt-Repository versioniert. Sie dient als verbindliche Wissensbasis für Installation, Betrieb, Sicherheit, Datenmodell, Sensorik, Historie, Zeitpläne, Automationen, GUI und DF100M-Integration.

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

## Projektstatus

Version: **v0.5 Full Platform Baseline**

Aktueller Fokus: Konsolidierung der v0.4.1 Local/Cloud-/BLE-Basis mit Installer, Hardening, RBAC, Datenbankmodellen, Sensorik, Historie und Automation.
