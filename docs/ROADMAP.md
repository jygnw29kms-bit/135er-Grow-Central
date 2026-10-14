# Roadmap – 135er-Grow Central

**Stand:** 2026-10-09
**Kanonischer Release-Status:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

Die frühere v0.3→v0.7-Funktionsliste ist historisch überholt. Das Projekt befindet sich aktuell bei `alpha-0.7.5`; gemäß dem kanonischen Release-Status ist Build 351 der veröffentlichte Raspberry-Pi-Hardwaretest-Candidate. Reale Hardwarevalidierung bleibt offen.

## Jetzt · Build 351 Hardwarevalidierung

- frischer Boot / Reboot;
- First Boot, Setup AP, DHCP/DNS;
- LAN/WLAN/mDNS und GUI-Persistenz;
- FRITZ! Smart Home / Tapo auf verfügbarer Zielhardware;
- Logitech C920/UVC;
- firmware-/modell-/USB-ID-bewusste LED-Fähigkeitserkennung;
- LED-Steuerung nur bei erkannter Unterstützung;
- Elecrow 7-Zoll Touch-Kiosk;
- Support-Bundle bei Abweichungen.

## Nächste Alpha-Ziele

### Umgesetzt im Entwicklungsstand vom 9. Oktober 2026

- Desktop/Mobile-Laufzeitstatus erkennt veraltete Cloud-Heartbeats und einen Wechsel des Cloud-Servers.
- Cloud-Ausfälle erzeugen Hinweise; lokale Kernfunktionen bleiben unabhängig davon verfügbar.
- Statusprüfungen behandeln fehlendes bzw. nicht antwortendes systemd und blockieren den asynchronen API-Ablauf nicht.
- Cloud-Adressen werden als reine HTTPS-Ursprünge ohne eingebettete Zugangsdaten geprüft.
- Cloud-Link V2 wiederholt den Diagnose-Handshake nach inkompatibler Health-Antwort oder fehlendem Telemetrie-Endpunkt.

Diese Änderungen sind Quellcodeverbesserungen und kein neuer veröffentlichter Image-Candidate. Quellen, Prüfungen und verbleibende Grenzen: [Analyse und Quellenabgleich](de/APP_REVIEW_2026-10-09.md).

### Geräte & Grow

- reale iConnect-Validierung für Mars Hydro FC3000 2024 und iFresh/DF100;
- DF100M BLE weiterhin als Diagnose-/Fallback-Pfad;
- Räume, Pflanzen und Growtagebuch weiter mit realen Sensordaten verbinden;
- Automationsregeln und Fail-safe-Verhalten auf realer Hardware absichern.

### Energie & Historie

- belastbare Zeitreihen für Stunde/Tag/Woche/Monat/Jahr;
- Kosten- und Verbrauchscharts;
- Datenretention und Export;
- Plausibilitätsprüfungen gegen reale Smart-Plug-Zähler.

### Mobile

- Nexus Mobile Android und iOS auf Realgeräten gegen den aktuellen Pi-Kandidaten testen;
- iOS-Sideload-Prozess reproduzierbar dokumentieren;
- sichere Serverzielverwaltung weiter verbessern;
- keine doppelte Geräteimplementierung in den Apps einführen.

### Cloud / Server / APT

- Cloud V6 auf Produktivserver reproduzierbar installieren/aktualisieren;
- Remotezugriff nur über TLS/HTTPS bzw. abgesicherten Tunnel;
- signierten APT-Pfad und Upgrade-/Rollback-Prozess weiter testen;
- Release-State und Prüfsummen bei allen öffentlichen Installerpfaden veröffentlichen.

### Security / Betrieb

- Rechte und Audit weiter härten;
- Backup/Restore real validieren;
- Update-/Rollback-Gates vervollständigen;
- Stable erst nach wiederholbaren Zieltests.

## Design

Alle neuen Pi-, Kiosk-, Mobile-, Website-, Repo- und Release-Oberflächen folgen dem [`GrowCentral Nexus UI`](DESIGN_SYSTEM_NEXUS.md). Logo und Branding bleiben unverändert.

## Stable-Gate

Eine Stable-/Beta-Hochstufung erfolgt erst, wenn die Kernpfade reproduzierbar auf Zielhardware getestet sind. Ein CI-erfolgreicher Build allein genügt nicht.

## Native Sensoraufnahme · Entwicklungsstand 13. Oktober 2026

Manuelle Aufnahme/Ablehnung, persistente Sperrzustände, Name/Raum-Zuweisung,
P-256-Geräteidentität und aktuelle Nonce-Prüfung sind im Backend und in der
Desktop-/Mobile-/Legacy-Oberfläche ergänzt. Firmware 0.3.0 baut für XIAO ESP32-C3;
Hardwarevalidierung bleibt offen. Netzwerk-MQTT benötigt individuelle TLS-Zugänge;
der anonyme Image-Listener ist auf Loopback begrenzt. BLE-Provisionierung und
automatische Geheimnisübertragung sind weiterhin offen und gesperrt.

Details, Migration und überprüfte Grenzen: [Sensoraufnahme](de/SENSOR_PAIRING.md).

## Home Assistant und Sprachassistenten — 2026-10-13

Installierbare lokale HA-Komponente mit Config Flow, Polling, Sensoren und
freigegebenen Schaltern. Separater API-Schlüssel und explizite Export-/Schaltlisten;
keine Rückexport-Schleife für importierte HA-Geräte. Weitere konfigurierte
Runtime-Sensoren können ausdrücklich als reine Messwerte ausgewählt werden.
Apple Home/Siri über HomeKit Bridge, Alexa/Google über HA Cloud oder die offiziellen
manuellen Account-Linking-Wege. Numerische Bodenfeuchte bleibt in HA; die aktuellen
HomeKit-/Google-Sensorklassen unterstützen sie nicht. Kontokopplung und reale
Sprachbefehle müssen auf der Zielinstallation geprüft werden.

Einrichtung: [Home Assistant](de/HOME_ASSISTANT.md).

## Geführte USB-Sensoraufnahme — 2026-10-13

USB-Kandidaten am Pi werden automatisch im Gerätebereich gezeigt. Der Assistent
prüft die aktuelle signierte USB-Identität, installiert bei Bedarf das geprüfte
XIAO-C3-Firmwarepaket 0.4.0, richtet WLAN und individuelle lokale MQTT-TLS-Zugänge
über USB ein und prüft danach dieselbe Identität im Netzwerk. Name/Raum und die
bewusste Aufnahme schließen den Ablauf ab. Widerruf und Schlüsselwechsel bleiben
manuell kontrolliert. Firmware wird im Image-CI separat gebaut und gebündelt;
Flashbereiche schließen NVS aus. Der lokale Broker-Helfer verwendet einen Unix-
Socket und öffnet keine allgemeine privilegierte Befehlsausführung.

Software-/Seriell-/TLS-Tests und Desktop-/Mobile-Dialog sind geprüft; tatsächliches
USB-Reset/Flash und WLAN auf XIAO/Pi bleiben Hardwaretests. BLE bleibt offen.
Anleitung: [USB-Sensor einrichten](de/USB_SENSOR_SETUP.md).
