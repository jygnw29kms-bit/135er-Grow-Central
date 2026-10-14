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

## Aktueller Sensorstand · 14. Oktober 2026

Firmware 0.4.1: USB-Aufnahme, MQTT über TLS und Bodenfeuchte-Anzeige auf einer Pi-4-Installation mit Hotfixes bestätigt. Das Original-Image 369 bleibt ein CANDIDATE und enthält Firmware 0.4.0. Kalibrierung, Dauerbetrieb und andere Hardwareklassen sind offen.

- [Sensor setup and calibration](../../docs/de/SOIL_SENSOR_GUIDE.md)
- [Hardware evidence and remaining checks](../../docs/de/SENSOR_HARDWARE_TEST_2026-10-14.md)
