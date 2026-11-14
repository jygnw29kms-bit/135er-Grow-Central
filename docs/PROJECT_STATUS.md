# Grow Central · aktueller Projektstatus

**Stand:** 14. November 2026 · **Entwicklung freigegeben** · **Raspberry-Pi-Quellstand abgeglichen**

## Maßgeblicher Pi-Livestand

| Merkmal | Verifizierter Stand |
|---|---|
| Hardware | Raspberry Pi 4 Model B, Debian 13 (aarch64) |
| Installationsbasis | `be24ba9097c2e98eb1e3f302b5992c004d2e6e29` |
| Betreiber-Build | `operator-be24ba9097c2-base508` |
| Distribution | `OPERATOR_PROVISIONED` |
| Git-Ziel | synchronisierte Pi-Laufzeit auf `master`, mit bewahrten Sicherheitserweiterungen |
| Letzter veröffentlichter Image-Candidate | `alpha-0.7.5`, Build 461; von diesem Livestand zu unterscheiden |
| Gesamte Image-Hardwareabnahme | nicht bestätigt |

## Pi ↔ GitHub Abgleich

- 871 ursprünglich versionierte Dateien überprüft; 19 Unterschiede untersucht, davon 3 projektbezogene Statusdateien.
- Der finale Sync-Branch enthält 755 byteidentische Pi-/Git-Dateien. 102 nur im Repository vorkommende CI-/Cloud-/Dokumentationsdateien bleiben erhalten.
- Die 20 verbleibenden Differenzen gegenüber der installierten Pi-Struktur sind bewusst aktuelle Dokumentations-, Test- und Sicherheitspfade; keine unbeabsichtigte Laufzeitdatei-Abweichung.
- Räume, Growbuch/Fotos, BLE, HomeKit, Pi-API und Final-Master-Weboberfläche mit Original-Git-Blobhashes gegenüber dem Pi bestätigt.
- Pi-spezifische HomeKit-Zubehörmodule, Mars-Hydro-Steuerungsmodule, PWA-Icons und das Sensor-Firmware-Prüfsummenmanifest sind in Git übernommen.
- Sicherheitskritische First-Boot-/sudo-/Netzwerkprüfungen aus dem neueren Git-Stand werden **nicht** auf ältere Pi-Versionen zurückgesetzt.
- Sensible Runtime-Daten, Zugangsdaten, private Provisionierung, historische Pflanzenbilder sowie nicht freigegebene Herstellerfotos werden nicht ins öffentliche Repository übertragen.

## Validierung

- **507 von 507 nicht-nativen Tests erfolgreich**; zwei native Mosquitto-Integrationsfälle wurden in der root-basierten QA-Umgebung ausgeschlossen.
- Die beiden Broker-Testdateien wurden separat unter dem Systembenutzer `mosquitto` mit **13 von 13 erfolgreichen Tests** geprüft; 26 Untertests ebenfalls bestanden.
- Python- und Shell-Syntax in einer von der produktiven Installation getrennten Git-Prüfkopie erfolgreich.
- Typische Geheimnis-/Token-Muster in geänderten Quelltexten ohne Treffer; kein Ersatz für einen umfassenden Security-Audit.
- Keine automatische Neuerstellung eines Images und kein ungeprüftes Deployment auf den laufenden Pi.

## Bekannte Grenzen und nächste Aufgaben

Die Historie, SQLite-Daten, Pflanzenbilder und übrigen lokalen Betriebsdaten sind **kein Teil** eines öffentlichen Quellcode-Backups. Ein vollständiges verschlüsseltes Systemabbild ist separat nötig. Einige Pi-exklusive Herstellerbilder sind wegen fehlender Weiterverteilungsrechte nur mit Quell- und SHA-256-Nachweis dokumentiert. Ein grafischer Build aus dem öffentlichen Repository braucht für diese Bildpfade rechtlich zulässige Assets.

Die reale End-to-End-Hardwareabnahme für alle Pi-Klassen, First Boot und alle Geräteprotokolle bleibt vom Quellcodeabgleich unabhängig offen.

**Details:** [Pi-/Git-Abgleichbericht](de/PI_GIT_RECONCILIATION_2026-11-14.md) · [Release State](../RELEASE_STATE.md) · [Pi-4-Abnahmeplan](de/PI4_END_TO_END_ABNAHME_2026-11-12.md).

## Nächste Integration: bereits abgenommener ESP32-Bodenfeuchtesensor

**Verbindlich:** Der vom Betreiber abgenommene ESP32-/XIAO-Bodenfeuchtesensor ist vorhandene, akzeptierte Hardware und muss in die vollständige Raum-Geräte-Pflanzen-Growbuch-Integration einbezogen werden. Die Hardwareabnahme darf nicht mit einer bereits vollständig getesteten aktuellen Ende-zu-Ende-Integration verwechselt werden.

- Sensor als echtes Gerät erfassen, identifizieren und dem Growzelt 100 × 100 × 200 cm sowie der betreffenden Pflanze beziehungsweise dem Pflanzentopf zuordnen.
- Die bereits vorhandene dreistufige Kalibrierung (lufttrocken, wassergesättigt, frisches Substrat) und ihre gültige Gerätezuordnung respektieren; keine unbegründete Neukalibrierung auslösen.
- Bodenfeuchte mit Messzeitpunkt, Einheit, Sensor-ID, Kalibrierstatus und Raum-/Pflanzenbezug als tatsächlichen Messwert speichern. Veraltete oder ungültig kalibrierte Werte kennzeichnen und nicht als aktuelle Messwerte ausgeben.
- Bodenfeuchte im Raum-Dashboard, in der Pflanzenansicht, in Growbuch-Foto-Snapshots, Langzeitverlauf und Grow-Vergleich anzeigen.
- HomeKit-Export der tatsächlichen Bodenfeuchte prüfen, getrennt von den Werten des HomePod und anderen Raumtemperatur-/Feuchtesensoren.
- Livekette ESP32 → MQTT/API → persistente Historie → PWA → Growbuch → HomeKit einschließlich Neustart/Wiederverbindung unter realer Hardware abnehmen.

**Reihenfolge:** gesichertes Pi-Backup, Raum-Geräte-Sensor-Zuordnung einschließlich des abgenommenen ESP32, Growbuch-/Livedaten-Verknüpfung, vollständige Liveabnahme. Die kulturübergreifende Architektur von Grow Central bleibt erhalten.
