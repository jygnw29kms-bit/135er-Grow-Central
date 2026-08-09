# 135er-Grow Central – Wiki Übersicht

## Plattform

Unterstützte Zielsysteme:

- Debian 12 / 13
- Ubuntu Server 22.04 / 24.04 LTS
- Raspberry Pi OS 64-bit auf Debian-Basis

Der Raspberry Pi ist die lokale Steuerinstanz. Ein Linux-VServer kann optional Telemetrie, Historie, Benutzerzugriff und Remote-Übersichten bereitstellen.

## Funktionsbereiche

- Benutzer, Rollen und Rechte (RBAC)
- Sites/Standorte und Geräte
- Sensoren und Messwerte
- Historie und Retention
- Zeitpläne
- Automationen
- Events und Alerts
- Audit-Logging
- Backup/Restore
- Cloud-Synchronisation
- DF100M BLE-Integration
- Responsive Web-GUI

## Sicherheitsprinzip

Lokale Funktionen dürfen nicht von der Cloud abhängen. Schreibende Fernbefehle sind explizit freizuschalten und werden lokal validiert. Secrets liegen außerhalb des Quellcodes in geschützten Konfigurationsdateien bzw. Umgebungsvariablen.
