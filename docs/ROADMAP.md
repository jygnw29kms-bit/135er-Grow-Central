# Roadmap – 135er-Grow Central

**Stand:** 2026-08-23  
**Kanonischer Release-Status:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

Die frühere v0.3→v0.7-Funktionsliste ist historisch überholt. Das Projekt befindet sich aktuell bei `alpha-0.7.5`; Build 118 ist der nächste Raspberry-Pi-Hardwaretest-Kandidat.

## Jetzt · Build 118 Hardwarevalidierung

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
