# Dauerhafte Grow-Historie (Stand: 13. November 2026)

## Zweck
Langzeitarchiv für Raumklima, Licht, Lüftung und künftig Wasser-/Substratwerte; Grow-Vergleich nach **Pflanzenalter (Woche 1–104)** statt Kalenderjahr. Daten gehen bei normalem App-/Pi-Neustart nicht verloren. Es gibt **kein automatisches Abschneiden bei 50.000 Messwerten**.

## Aktive Installation auf dem Test-Pi
- **Datenbank:** `/var/lib/135er-grow-central/history.sqlite3` (SQLite WAL).
- **Erfassung:** `grow-central-mars-history.timer` ruft `grow-central-mars-history.service` alle 5 Minuten auf. Nur BLE-Notify, **keine Steuerbefehle**. FC3000 und DF150-M werden unabhängig voneinander gelesen.
- **Raumsensoren:** Der bestehende 5-Minuten-Raum-Sampler archiviert seine bestätigten Messwerte zusätzlich in SQLite. Er setzt weiterhin eine bereits vorhandene Raum- und Gerätezuordnung voraus.
- **Backup:** `grow-central-history-backup.timer` erstellt jeden Tag um ca. 03:20 einen SQLite-Onlinebackup-Snapshot unter `/var/lib/135er-grow-central/history-backups/history-YYYYMMDD.sqlite3.gz` und prüft vor dem Komprimieren `PRAGMA integrity_check`.
- **Aufbewahrung:** mindestens 30 letzte Tagessnapshots sowie ein Monatssnapshot je Monat bis zu 60 Monate; die Hauptdatenbank läuft unbefristet weiter, solange Speicherplatz vorhanden ist.
- **Betriebsstatus bei erster Installation:** SQLite und API laufen, FC3000-Datensätze erfolgreich gespeichert. MZF002-BLE-Advertising ist intermittierend; fehlende Scan-Fenster werden nicht als Nullwerte gespeichert, sondern im Journal angezeigt.

## API
Alle neuen Endpunkte benötigen die normale authentifizierte GUI-Sitzung oder den lokalen API-Token.

| Methode | Endpoint | Zweck |
| --- | --- | --- |
| GET | `/api/v1/history/status` | Anzahl, ältester und jüngster Messzeitpunkt |
| GET | `/api/v1/history/points?room_id=...&metric=...&start=...&end=...&limit=500` | Chronologischer Messverlauf |
| GET | `/api/v1/history/summary?room_id=...&start=...&end=...` | Anzahl, Minimum, Maximum, Durchschnitt über **alle** Treffer |
| GET | `/api/v1/history/export.csv?room_id=...&start=...&end=...` | Streaming-CSV ohne 50k-Zeilenlimit |
| GET | `/api/v1/history/bindings` | Mars-Hydro-Geräte-Raumzuordnungen |
| POST | `/api/v1/history/bind-device` | JSON `{"device":"mars-hydro-mzf002","room_id":"<vorhandene-room-id>"}` bzw. `mars-hydro-fc3000` |
| GET | `/api/v1/history/compare-plants?plant_a=...&plant_b=...&weeks=16` | Vergleich je relative Grow-Woche |

**UI:** `/static/console.html` → Räume → Sensordaten: Langzeitarchiv, CSV und Mars-Hydro-Raumzuordnung. Räume → Pflanzen: Auswahl zweier Pflanzen und Wochenvergleich.

## Datenquellen und Kennzeichnungen
- `measured`: lokal empfangene Temperatur, relative Luftfeuchte, RPM, Bodenfeuchte etc. (nur wenn tatsächlich vorhanden).
- `reported_setpoint`: tatsächlich gemeldeter Lüfter-/Licht-Sollwert, keine sensorisch gemessene Lichtleistung.
- `reported_state`: Schaltzustand.
- `estimated_show_only`: aus Sollwert abgeleitete Hersteller-Schauwerte. CFM = max(0, 19 + 3.8 × Lüfter-%); Pa = max(0, 5.6 × Lüfter-% − 90); bei AUS sind beide 0. **Nicht für Regelung oder Fehlerdiagnose verwenden.**

Vergleich nach Pflanzenalter funktioniert für alle angelegten Kulturen, nicht bloß Cannabis. Zwei Pflanzen in demselben Raum teilen sich dessen Raumklima, nicht aber zwingend ihre Bodenfeuchtemesswerte. Die API weist ausdrücklich auf diesen Unterschied hin. Ein Grow aus einem Vorjahr, für das niemals Messwerte erfasst wurden, bleibt **ohne Daten**; er wird nicht rückwirkend simuliert. An-/Abbau und Pumpenereignisse gehören in die vorhandenen Raum-/Pflanzenjournale.

## Installieren der Systemdienste (neues Testimage)
```bash
sudo install -m 0644 deploy/systemd/grow-central-mars-history.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/grow-central-mars-history.timer /etc/systemd/system/
sudo install -m 0644 deploy/systemd/grow-central-history-backup.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/grow-central-history-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now grow-central-mars-history.timer grow-central-history-backup.timer
```

## Wiederherstellen
Vor Wiederherstellung den Grow-Central-Service und die beiden Timer beenden, eine Kopie der aktuellen SQLite-Datenbank sichern und dann eine geprüfte `.sqlite3.gz`-Sicherung entpacken. Dateibesitzer `growcentral:growcentral` und Berechtigungen `0600` wiederherstellen, anschließend Dienst starten und `/api/v1/history/status` kontrollieren. Keine Live-Datenbank während laufendem WAL-Betrieb mit einfachem `cp` sichern; die tägliche Backupfunktion verwendet gezielt SQLite `Connection.backup`.

Lokale Backups allein schützen **nicht** gegen vollständigen SSD-/Pi-Ausfall oder Diebstahl. Für dauerhaft mehrjährige Archivierung ist zusätzlich ein verschlüsselter Offsite-Export nötig; derzeit **nicht** automatisch konfiguriert.
