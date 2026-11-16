# Grow Central · aktueller Projektstatus

## Beta-1.0-GUI-Abnahme und Kamera-Watchdog (16.11.2026)

**Manuelle Abnahme:** 72 von 110 Einzelprüfungen bestanden, 8 Fehler, 30 offen. Separat: sieben Benutzerverwaltungsfunktionen in LAN und Cloud noch nicht als vollständige Final-Master-GUI verfügbar. Dieses Dokument ist keine Produktivfreigabe.

**Diagnose auf Live-Pi (nur lesend):** Logitech C920 USB-ID 046d:082d, /dev/video1 und /dev/video2 vorhanden; ffmpeg hält /dev/video1 offen. Lokaler Stream antwortet HTTP 200, Cloud-Vorschau meldet wiederholt 503. Mehrfache lokale Stream-Aufrufe können sich gegenseitig verdrängen, weil derzeit ein aktiver globaler Capture-Prozess verwendet wird. Kamera-Frame-Lieferung und die Ursache der Stream-Konkurrenz sind noch nicht end-to-end abgenommen.

**Reparatur-Branch:** `fix/beta1-gui-camera-controls-20261116` / Draft-PR #102, ausdrücklich **nicht produktiv deployed**. Entwickelt sind: owner-geschützte bounded Watchdog-Diagnose ohne Bild-/Token-Speicherung (Frame-Alter, ffmpeg-Ausfall, Stream-Verdrängung und Preview-503), Kamera-Start/Stopp-Bedienelemente in LAN/Cloud, Schalterzustand Rot/Aus und Grün/Ein nur auf Basis frischer BLE-Rückmeldung, Growbuch-Navigation im lokalen HTML sowie gleiche Darstellung gespeicherter Messmomentaufnahmen in LAN und Cloud.

**Verbleibende Beta-Blocker:** F-001 vollständiger Kamerabildnachweis, F-003 Growbuch-Snapshot von Pi bis Cloud mit echter Pflanze/korrekt abgeschlossenem Pflanzenprofil, F-004 Schreib-Synchronisierung LAN↔Cloud, F-005 Besitzer-/Mitglieder-GUI und sichere Cloud-Gast-ACL, F-002 Kamerastopp im echten Browser. V-002 vollständige visuelle Parität und V-001 Farbschalter benötigen reale Endabnahme. Kein Release mit unkontrolliertem Guest-WebSocket.

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

## Rückgängig machbare Raum- und Gerätezuordnung

Die Raumverwaltung unterstützt jetzt als Entwicklungsstand die reversible Archivierung von Räumen. Beim Archivieren werden zugeordnete Geräte freigegeben und anschließend als „nicht zugeordnet“ angezeigt. Hardware wird dadurch weder gelöscht noch zurückgesetzt. Zugehörige Pflanzen, Growbuch-Einträge, Fotos und historische Sensormessungen bleiben mit ihrer ursprünglichen Raum-ID erhalten. Ein archivierter Raum kann mit derselben ID wiederhergestellt werden; Geräte müssen dann bewusst erneut zugeordnet werden.

Die separate Trust-Information des abgenommenen ESP32-Bodenfeuchtesensors wird beim Freigeben der Raumzuordnung ebenfalls aktualisiert, ohne Geräteidentität, Annahmestatus oder Kalibrierung zu entfernen. Eine unabsichtliche Zuweisung zu einem fremden Raum darf beim Abwählen nicht entstehen. API-Schreibaktionen bleiben authentifizierungspflichtig.
