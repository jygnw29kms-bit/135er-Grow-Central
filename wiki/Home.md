# 135er GrowControl Wiki

**135er GrowControl** ist eine Local-First-Steuer-, Monitoring- und Automationsplattform auf Raspberry-Pi-/Debian-Basis mit optionaler Linux-VPS-Cloud.

> Der Raspberry Pi bleibt Master. Die Cloud ist optional. DF100M-Schreibzugriffe bleiben experimentell, bis reale Hardwaretests das Protokoll validieren.

## Einstieg

- [Projektgeschichte](de/PROJEKTGESCHICHTE.md) – von der Idee bis zum Hardware-Teststand
- [Projektstatus](de/PROJEKTSTATUS.md) – implementiert vs. experimentell vs. geplant
- [Architektur](de/ARCHITEKTUR.md)
- [Installation](de/INSTALLATION.md)
- [Raspberry Pi Test Image](de/RASPBERRY_PI_3B_TEST_IMAGE.md)
- [Sicherheit](de/SICHERHEIT.md)
- [DF100M](de/DF100M.md)
- [GUI](de/GUI_UND_RESPONSIVE_DESIGN.md)
- [Cloud](de/CLOUD.md)
- [Datenbanken](de/DATENBANKEN.md)
- [Benutzer & Rechte](de/BENUTZER_UND_RECHTE.md)
- [Sensoren & Historie](de/SENSOREN_UND_HISTORIE.md)
- [Zeitpläne & Automationen](de/ZEITPLAENE_UND_AUTOMATIONEN.md)
- [Backup & Wartung](de/BACKUP_UND_WARTUNG.md)

## English

- [Project History](en/PROJECT_HISTORY.md)
- [Project Status](en/PROJECT_STATUS.md)
- [Architecture](en/ARCHITECTURE.md)
- [Installation](en/INSTALLATION.md)
- [Raspberry Pi Test Image](en/RASPBERRY_PI_3B_TEST_IMAGE.md)
- [Security](en/SECURITY.md)
- [DF100M](en/DF100M.md)
- [GUI](en/GUI_AND_RESPONSIVE_DESIGN.md)
- [Cloud](en/CLOUD.md)

## Aktueller Meilenstein

**v0.5.x Hardware Validation**

Aktueller Fokus:

1. reproduzierbares Raspberry-Pi-3B-Testimage;
2. erster realer Pi-Boot;
3. DF100M Discovery/GATT/Notifications;
4. Legacy-Korrelation bei definierten Lüfterwerten;
5. kontrollierte Payload-Validierung.

## Verbindliche Fakten zum Testgerät

```text
Identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID:  A0A3B35EFDC8
Firmware:   V1.8
```

## Architekturgrundsätze

- kein ESP32 im Core;
- lokale Funktionen ohne Cloud;
- Pi → Cloud ausschließlich ausgehend über HTTPS;
- kein öffentliches Pi:8080;
- Remote Commands als lokal validierte Requests;
- SQLite lokal, PostgreSQL als Cloud-Ziel;
- responsive Browser-GUI für Desktop bis iPad/Smartphone;
- experimentelle Schreibzugriffe standardmäßig aus.

Die vollständige technische Projektdokumentation liegt zusätzlich unter `docs/` im Hauptrepository.
