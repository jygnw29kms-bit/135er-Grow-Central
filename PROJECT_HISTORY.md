# 135er GrowControl – Projektgeschichte / Project History

Dieses Dokument ist die chronologische, technische Projekterzählung von der Ursprungsidee bis zum aktuellen Hardware-Teststand. Es trennt bewusst Idee, Beobachtung, implementierte Funktion und geplante Plattformfunktion.

## 1. Ursprungsidee

Ausgangspunkt war ein praktisches Problem: Der Mars Hydro DF100M ließ sich im vorhandenen Setup zuverlässig über die **Mars Legacy App** nutzen, während die neuere Mars-Hydro-App im konkreten Fall nicht funktionierte. Daraus entstand die Frage, ob ein Raspberry Pi die zentrale lokale Steuer- und Monitoring-Instanz übernehmen kann.

Ziel war von Anfang an eine Browser-GUI, die dauerhaft auf einem Tablet/iPad laufen kann und nicht von einer Hersteller-Cloud abhängt.

## 2. Referenzrecherche

Als technische Inspiration wurde das Open-Source-Projekt `KillerInk/GrowFanController` betrachtet. Die dort verwendete ESP32-Richtung wurde bewusst **nicht** übernommen. Für 135er GrowControl wurde Raspberry Pi als einzige lokale Masterplattform festgelegt.

Parallel wurden Herstellerseiten, Mars-Hydro-App-/Legacy-Informationen, Google-Play-Angaben und die bereitgestellte Legacy-App analysiert. Quellen werden im Projekt mit Herkunftskategorien geführt:

- `[MARS-OFFICIAL]`
- `[GOOGLE-PLAY]`
- `[OPEN-SOURCE]`
- `[APK-OBSERVATION]`
- `[EXPERIMENTAL]`

## 3. DF100M Reverse Engineering

Aus der Legacy-App-Analyse wurden relevante Zeichenketten und BLE-Hinweise identifiziert. Dazu zählen:

```text
MZ_MZF
MZ_MZF002
Fan type
Wind Speed
wind_speed
wind_speed_num
wind_set_speed
wind_save_enable
RPM
flutter_reactive_ble
discoverServices
writeCharacteristicWithResponse
NotifyCharacteristicRequest
```

Für das konkrete Testgerät wurden folgende Daten festgehalten:

```text
Identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID:  A0A3B35EFDC8
Firmware:   V1.8
```

Kandidaten-UUIDs:

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e
83677baa-3eb8-4866-b6b6-96e5ed5cc48d
f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

Wichtig: Kandidatenstatus ist kein Validierungsstatus. Erst reale Capture-/Replay-Tests dürfen eine UUID oder ein Payloadformat als bestätigt markieren.

## 4. Frühe Laufzeit

Die erste lauffähige lokale Basis wurde als FastAPI-/Bleak-Anwendung aufgebaut. Sie ermöglicht Discovery, Verbindung, GATT-Inspektion und Notification-Capture. Für Geschwindigkeitsschreibtests wurden mehrere experimentelle Payloadmodi vorgesehen:

- `byte`: `bytes([percent])`
- `ascii`: ASCII-Darstellung des Prozentwertes
- `hexprefix`: `[0x01, percent]`

Schreibzugriffe wurden aus Sicherheitsgründen mit `DF100M_ALLOW_WRITES=false` standardmäßig deaktiviert.

## 5. GUI-Entwicklung

Die frühe Weboberfläche wurde in Richtung eines futuristischen, dunklen HUDs weiterentwickelt. Das Zielbild umfasst Navigation für Dashboard, Geräte, Sensoren, Historie, Zeitpläne, Automationen, Cloud und System.

Die aktuelle grafische Referenz liegt unter:

```text
docs/assets/gui/gui-preview-v0.5.png
```

Das Design ist responsiv vorgesehen für:

- großer Desktop: >= 1400 px
- Desktop/Notebook: 1024–1399 px
- Tablet/iPad: 768–1023 px
- Smartphone: < 768 px

## 6. Local-first wird Plattformarchitektur

Aus dem reinen Fancontroller wurde eine allgemeine Plattformarchitektur. Feste Grundsatzentscheidung:

```text
Browser/iPad
   |
135er GrowControl Local
Raspberry Pi
   |
   +-- BLE --> DF100M
   +-- SQLite / automation / schedules
   +-- outbound HTTPS --> optional Linux VPS
```

Der Pi bleibt Master. Die Cloud darf lokale Steuerung nicht blockieren und ist kein Single Point of Failure.

## 7. Cloud-Alpha

Eine optionale Cloud-Basis wurde ergänzt. Sie unterstützt Telemetrie, aktuelle Werte, Historienabfrage sowie einen vorbereiteten Command-Flow. Die Pi-Seite synchronisiert ausschließlich ausgehend über HTTPS.

Remote Commands bleiben doppelt abgesichert: Cloud-Funktion und lokale Pi-Funktion müssen explizit aktiviert sein; Ziel, Aktion und Wert werden lokal validiert.

## 8. Full Platform Baseline v0.5

Die Plattformplanung wurde um folgende Domänen erweitert:

- Benutzer
- Rollen und Berechtigungen
- Sessions
- Sites
- Geräte
- Sensoren
- Messwerte / Historie
- Zeitpläne
- Automationsregeln
- Events
- Alerts
- Commands / Results
- Audit Log
- Einstellungen
- Cloud Nodes
- Backups

Lokale Datenhaltung: SQLite. Cloud-Ziel: PostgreSQL.

Die Rollen wurden konzeptionell festgelegt:

- Admin
- Operator
- Viewer
- Device/Agent

Die v0.5-Baseline enthält Datenbankschemata, Installer-/Hardening-Richtung und zweisprachige Plattformdokumentation. Nicht jede dieser Funktionen ist bereits vollständig als Runtime verdrahtet.

## 9. GitHub-Konsolidierung

Das Projekt wurde unter `jygnw29kms-bit/135er_GrowControl` konsolidiert. Frühere Arbeitsstände und ZIP-/Bundle-Artefakte sind historische Zwischenstände und nicht mehr die führende Quelle. `master` ist die maßgebliche Codebasis.

Die Wiki-Dokumentation wird zusätzlich im Verzeichnis `wiki/` versioniert, damit Wissen nicht von der GitHub-Wiki-Sonderrepository-Struktur abhängt.

## 10. Raspberry-Pi-3B-Testimage

Für die ersten realen Hardwaretests wurde ein reproduzierbarer GitHub-Actions-Imagebuilder aufgebaut. Ziel ist ein flashbares Raspberry Pi OS Lite 64-bit / Debian 13 Image mit vorinstalliertem GrowControl.

Temporäre Testparameter:

```text
Hostname: growcontrol-test
SSH user: test
SSH password: test
API/application token: test
Web UI: http://<PI-IP>:8080
```

Sicherheitskritische Funktionen bleiben deaktiviert:

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

### Build-Lernschritte

**Build 1:** Root-Dateisystem lief voll, weil das heruntergeladene Basisimage versehentlich in das Zielimage kopiert wurde. Korrektur: Buildartefakte aus `rsync` ausschließen und Image/Root-Partition vorab vergrößern.

**Build 2:** Imagecustomizing und Python-Pakete liefen durch; UFW scheiterte im ARM-chroot mit `Couldn't determine iptables version`. Korrektur: Firewall wird nicht mehr im chroot initialisiert, sondern über einen First-Boot-systemd-Service auf der realen Pi-Kernelumgebung.

## 11. Nächster Meilenstein

Der nächste technische Meilenstein ist der reale Raspberry-Pi-/DF100M-Test:

1. Image flashen und booten.
2. Netzwerk, SSH, systemd, Web UI und Bluetooth prüfen.
3. Mars Legacy App vollständig schließen, damit BLE frei ist.
4. DF100M per `bluetoothctl` und GrowControl Discovery identifizieren.
5. GATT-Services/Characteristics erfassen.
6. Notifications aufnehmen.
7. Legacy-Verhalten bei 10/30/50/70/90 % beobachten.
8. Payloadhypothesen als `candidate → observed → replayed → validated` dokumentieren.
9. Erst danach Schreibzugriffe kontrolliert freischalten.

## English summary

135er GrowControl started as a practical attempt to replace permanent vendor-app dependency for a Mars Hydro DF100M with a local Raspberry Pi controller. It evolved into a local-first platform with BLE adapters, responsive web UI, local persistence and automation, optional outbound-only cloud synchronization, security boundaries, RBAC/data-model planning and a reproducible Raspberry Pi test-image pipeline. The next milestone is real hardware validation; DF100M write protocol support is deliberately still considered experimental.
