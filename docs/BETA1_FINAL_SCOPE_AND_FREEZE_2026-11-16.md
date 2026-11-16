# 135er-Grow Central: Beta-1.0-Leistungsumfang und Feature-Freeze

Stand: 16.11.2026 · **verbindlicher Betreiber-Scope, keine Beta-Freigabe**.

## Beschluss und Schutz gegen Scope Creep

Grow Central ist **eine rein private Einzelzelt-App** für ein bestehendes Zelt (100 × 100 × 200 cm) mit Raspberry Pi 4 als lokaler, offlinefähiger Steuer- und Datengrundlage. Die **bestehende verschlüsselte Cloud/PWA-Fernbedienung bleibt Pflichtfunktion**, nicht optionales Extra. Mehrere Benutzer dürfen auf **dasselbe** Zelt zugreifen, aber ausschließlich mit rollenbasierten, serverseitig geprüften Rechten. Eine separate kommerzielle/Enterprise-/Mehrzelt-Version ist nicht Teil dieses Projekts.

Ab diesem Scope-Beschluss gilt:
1. **Keine neuen Features, zusätzlichen Kulturen-/Hardwareintegrationen, UI-Redesigns, Farben oder Marketingprojekte** während der Beta-Stabilisierung. Bereits ausdrücklich vereinbarte, noch fehlende Beta-Funktionen dürfen bis zu ihrer Erfüllung fertiggestellt werden. Das ist kein neuer Feature-Wunsch.
2. Die **zuletzt in master implementierte 135er-Sidebar-Marke** (Hexagon/Trennlinie, „135er-Grow Central“, Unterzeile „ENVIRONMENT CONTROL SYSTEM“) ist eingefroren. Das Final-Master-Layout muss bei jedem Fix auf LAN und Cloud identisch bleiben; nur Transport und Login dürfen technisch unterschiedlich sein.
3. Neue Anforderungen landen mit Begründung im **Nach-Beta-Ideenparkplatz**, werden nicht automatisch implementiert. Sicherheits-, Datenintegritäts-, Zugänglichkeits- und Fehlerkorrekturen sind vom Freeze ausgenommen.
4. Nie Pi-/Cloud-Release allein aufgrund grüner CI; Backup, Rollback, Security Gates, echte Pi-Hardware und iPhone LAN/CLOUD E2E müssen bestanden sein. Keine nicht freigegebenen Gäste, keine automatischen Hardwarebefehle ohne failsafe-geprüfte Aktoren.
5. Dokumentierte ältere Universal-/Open-Source-/Mehrraum-/Marktpositionierungsabschnitte sind historischer oder repositoryweiter Hintergrund, **keine Autorisierung zur Ausweitung des privaten Betreiberumfangs**. Bestehende GitHub-Lizenz und öffentliche Quellcode-Historie werden durch diesen Scope-Beschluss nicht rückwirkend geändert. Keine Geheimnisse oder Kundendaten im öffentlichen Git.

## Verantwortliche Installations-/Datenarchitektur

- **Ein Zelt, ein maßgeblicher lokaler Datenbestand auf dem Pi**; persistente Messhistorie und Growbuch mit Pflanzen-/Geräte-/Zeitbezug. Cloud ist authentifizierter Fernkanal und darf keinen konkurrierenden Growdatenbestand schaffen.
- **Offline:** Lokale Sensorik, Zeitpläne (sobald freigegeben), Historie, Benutzerberechtigungen aus lokal gültiger Autorisierung und manuelle Steuerung funktionieren ohne Internet. Ausfall/Veraltung sichtbar, keine Fantasie-Livewerte. Cloud-Ausfall darf kein automatisches Gerät-Reset auslösen.
- **Geräte im Zelt:** Mars Hydro FC3000 (Licht BLE), DF150-M (Abluft BLE), vorhandener XIAO ESP32-C3 Bodenfeuchteknoten/USB/MQTT, Logitech C920, Apple-Home-Bridge. Vorhandene Kalibrierung und reale Zuordnung bleiben erhalten. Kein zweites Zelt als Ziel.
- **Klima-Nodes:** SHT45 + XIAO ESP32-C3 als eigenständige WLAN-Knoten für unten/Pflanzenhöhe/oben sind **vereinbarte Hardwareausbau-Option**. Drei Punkte nur nach physischer Installation und realer Validierung; kein fiktiver Sensor oder ungetestete Livewerte. Hardware-Nichtvorhandensein blockiert nicht die Software-Beta. Siehe `docs/SENSOR_SUPPORT_MATRIX.md` (`vendor_verified`, noch kein Grow-Central-Hardwaretest).
- **Nicht Bestandteil Beta 1.0:** kommerzielle Rollen/Abos, Enterprise/Mehrzelt, zusätzliche Hub-/Marktplatzarchitektur, CO2/PPFD-Ausbau, Tapo/Shelly/Zigbee/RS485-Integration als neue Arbeiten, neue 3D-Gehäuse oder ein zweites Redesign. Bestehende Codepfade dürfen erhalten bleiben, aber keine Zusatzpriorität.

## Umfang und Quelle der Nachweise

Legende: `MANUELL OK` vom Besitzer am iPhone; `CODE` vorhandene Implementierung ohne ausreichenden Endtest; `OFFEN` nicht geprüft; `FEHLER` gemeldete Fehlfunktion; `GESPERRT` aus Sicherheitsgründen nicht scharf.

**Manuelle GUI-Bilanz (16.11.):** 110 geplante Einzelprüfungen, davon 72 OK, 8 FEHLER, 30 offiziell nicht getestet (LAN 36 OK/4 Fehler/15 offen; Cloud 36 OK/4 Fehler/15 offen). Zusätzlich sieben Benutzer-GUI-Funktionen auf beiden Zugriffswegen nicht als vollständige Final-Master-Funktion erreichbar (14 Verfügbarkeitslücken); diese bleiben offiziell „nicht getestet“, bis die GUI implementiert ist. Die manuelle Bilanz verändert sich nicht durch Unit-Tests.

### Bereits manuell auf LAN und Cloud als OK gemeldet
- Login, Navigation, PWA-Start auf iPhone 17 Pro Max, Logout/Login, Responsive-Darstellung.
- Live-Temperatur, Luftfeuchte, Bodenfeuchte, Reihenfolge Temperatur → RH → Soil → Licht → Lüfter, phasengerechte Klimabewertung, Systemstatus.
- Lichtstatus, Licht Ein/Aus, Dimmen, Lüfterstatus, Ein/Aus, Drehzahl; Geräteliste. Gerätezuordnung und Sensorstatus/Kalibrierung inzwischen ebenfalls je Zugang OK.
- Raum ansehen/archivieren, Pflanzen anlegen/bearbeiten, Phase wechseln, Growbuch anlegen/Fotos/erneut öffnen.
- Messhistorie und zeitlicher Vergleich; Apple-Home-Bridge-Status und bestehende Kopplung.
- Cloud-Zugang, gleiche Messwerte, visuell bedienbare Oberfläche (aber **nicht** 100 % identisch), erkennbare Verbindungsunterbrechung.

### Reale Fehler / Verbesserungen, die vor Freeze-Abnahme zu schließen sind
| ID | Priorität | Befund | Annahme / Abnahme |
|---|---|---|---|
| F-005 | **P0 Sicherheit** | Besitzer-/Mitglieder-/Einladungs-/Rollen-GUI fehlt im Final Master auf LAN und Cloud | Eigene Konten Owner/Admin/Grower/Beobachter, Einladungen QR/Link, Annahme, sofortiger Widerruf, serverseitige ACL für jede Lese-/Schreibaktion, Cloud-Gäste ohne Owner-API, 2 echte Konten auf iPhone |
| F-004 | **P1 Daten** | Änderungen LAN ↔ Cloud nicht zuverlässig sichtbar | Ein Testeintrag auf jeder Seite wird auf der Gegenseite nachweislich gespeichert, aktualisiert, erneut geladen; kein fälschliches „gespeichert“ oder divergentem Cache |
| F-003 | **P1 Daten** | Sensorwerte im Growbuch nicht korrekt verknüpft | Zeitgestempelter Sensor-Snapshot mit Temperatur/RH/Soil, Gerätequelle, Raum/Pflanze und Veraltungskennzeichnung; korrekt in LAN und Cloud nach Neustart; kein Überschreiben historischer Momentaufnahmen |
| F-001 | **P1 Kamera** | C920-Bild öffnet in LAN und Cloud nicht | Echtes JPEG und laufende Anzeige auf beiden Wegen, gerätesicherer ffmpeg-Watchdog, keine konkurrierenden Capture-Prozesse, 503/Timeout-Recovery ohne Endlosschleife |
| F-002 | **P1 Kamera** | Kamerastream lässt sich im Final Master nicht gezielt beenden | Start/Aktualisieren/Beenden in beiden PWAs; Stop beendet eigene Bildanforderung und hält Viewer an, sauberer Neustart; Sicherheitsprüfung bei mehreren Viewern |
| V-002 | **P1 UI-Vertrag** | LAN und Cloud nicht vollständig identisch | Menü, Räume, Benutzerverwaltung, Growbuch, Anzeige und Statussemantik im aktuellen 135er-Branding auf iPhone visuell gleich; parity-CI + Screenshotprüfung |
| V-001 | **P2 UI** | Lichtschalter soll Grün bei AN/Rot bei AUS zeigen | Anzeige basiert auf bestätigtem BLE-Istwert, nicht nur Buttonklick; „unbekannt“ neutral; gleicher LAN-/Cloud-Stil |

### Vereinbarte Beta-Funktionen mit noch offener Freigabe
| Bereich | Tatsächlicher nachgewiesener Git-Stand | Noch zu tun / Gate |
|---|---|---|
| Benutzer/Einladungen | Lokale `room_members`/`room_sharing`; Cloud-`/api/v2/collaboration`, Cloud-`join-room.html`, isolierter Gast-WebSocket/ACL laut `docs/BETA1_RELEASE_GATES.json` teilweise integriert | Vollständige **Besitzer-GUI**, identische LAN/Cloud-Rollenabfrage, owner/guest Token- und Sessionabläufe, sofortiger Widerruf, zwei echte Konten; keine unkontrollierte Öffnung bisheriger Owner-Sockets |
| Licht- und Lüfter-Automationen | `app/room_control_plans.py`: `simulation_only_not_armed`; Lichtfenster/Lüfter-Schwellen/Failsafe-Vorschau | UI zu Ende führen; realer BLE-Hardwaretest inkl. Sommer-/Winterzeit, Ausfall, Override, Hysterese, Kollision HomeKit/GUI; nur danach scharf schalten |
| Warnungen und Push | Lokale Benachrichtigungs- und Subscription-API/Worker vorhanden | Cloud-Kontobindung, HTTPS/VAPID/Opt-in, Alarmzustände, Ruhezeiten, Widerruf und **echte Pushzustellung** auf iPhone nachweisen |
| Kamera-Watchdog | Repo-`app/camera.py` hat watchdog/aktiven ffmpeg-Stream; Live-Pi erkennt C920 (046d:082d, /dev/video1, /dev/video2), aber Cloud Preview lieferte wiederholt 503 | Capture-Konkurrenz eliminieren, Full-Frame-Liveness, bounded Recovery und Diagnoselogs, E2E auf iPhone |
| Growbuch/Historie | Persistenz, Snapshot-Backend und Foto-Pfad vorhanden | Korrekte Detailanzeige, Messzeit/Sensor/Soil und Raum-/Pflanzenreferenz, Cloud-Leseschreibparität, Backup/Restore |
| PWA und Designs | Aktuelles Sidebar-Branding in `master` LAN/Cloud; individuelle Transport-Skripte | Einheitliche Final Master GUI, Cache-Versionen, Safari/PWA-Tests |
| Installation/Wartung | Pi4 mit autostart SSH/MeshCentral und Cloud-Kanal; Release-Report dokumentiert Backup-Audit | Getestete Wiederherstellung, verschlüsselte Backups, Ausfallszenarien, Update/Rollback, Log-/Secret-Schutz |
| Apple Home | Vier veröffentlichte Geräte, Nutzer meldet Bridge und Kopplung OK | Kein Doppelgerät; Funktionen/Raum-Sichtbarkeit und tatsächliche Werte nach Neustart prüfen |
| SHT45-Klima-Nodes | Katalog-/Treiberunterstützung `vendor_verified` | Keine Beta-Live-Freigabe bis reale Node-Hardware vorhanden und geprüft |

## Umsetzungsfolge / Arbeitsmodus bis zum Bugfix-only-Zustand

**Phase A (jetzt):** Scope einfrieren, Branding- und CI-Parität sichern, P0 Benutzerrechte und Login/Cloud-Gast-Endtest vollständig implementieren.

**Phase B:** F-004 Datenautorität und Sync, F-003 Growbuch-Snapshots, F-001/002 Kamera mit Capture-Watchdog und Stopp, V-001/002 GUI-Anpassungen abschließen.

**Phase C:** Bestehende Beta-Zusagen (Automationen, Warnungen, Push, Backup/Restore, Offline) fertig integrieren und auf realen Geräten prüfen; fehlende physische SHT45-Nodes bleiben dokumentierte optionale Ausbaustufe, keine Blocker.

**Phase D – eigentlicher BUGFIX ONLY:** Sobald **alle verpflichtenden Beta-Funktionen in Code implementiert sind**, werden Feature- und Designänderungen komplett eingefroren; danach nur noch Fehlerbehebung, Sicherheitsupdates, Regressionstests und Dokumentation. Beta-Freigabe erst, wenn alle Pflichtgates in `docs/BETA1_RELEASE_GATES.json` mit realen Nachweisen bestanden und alle schweren Fehler geschlossen sind.

### Definition of Done pro Ticket
- Reproduzierbarer Fehler / erwartetes Verhalten mit Status LAN und Cloud.
- Isolierter Fix ohne unnötiges UI-/Feature-Churn; kein Branding- oder Datenverlust.
- Automatisierter Regressionstest; Sicherheits- und API-ACL-Test bei Schreibzugriff.
- Pi-/Cloud-Deployment getrennt mit Sicherung, Prüfsumme, Rollback.
- iPhone-17-Pro-Max-Abnahme LAN und Cloud; Neustart/Offline-Prüfung, falls relevant.
- Git-Commit, Release-Gate, README/Changelog und dokumentierte Freigabe.
- Die ursprünglichen 110 Manuallisten bleiben maßgeblich; kein automatisches Schönrechnen.

## Nicht automatisch zu ändern

Kein produktiver Nutzer, Invite, Sensor-Offset, Kalibrierwert, Growbuch-Eintrag, Fotos, Kamera-Berechtigung, Lampen-/Lüfterstellung oder Rootserver-Zugriffsrecht darf beim Scope-Freeze verändert werden. Keine neuen Public-Images, keine Änderung der bestehenden Lizenz ohne gesonderten Beschluss.

**Konsequenz:** Dieser Freeze friert **Entscheidungen und den akzeptierten Zielumfang** ein; er behauptet weder, dass die sieben Bugs behoben, noch dass Beta 1.0 bereits freigegeben ist.
