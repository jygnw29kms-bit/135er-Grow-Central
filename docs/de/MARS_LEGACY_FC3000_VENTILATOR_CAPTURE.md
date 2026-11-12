# Mars Legacy: FC 3000 und Ventilator parallel analysieren (2026-11-12)

## Aktueller Umfang

- FC 3000: Geräte-ID aus Mars Legacy bestätigt, Firmware V3.4, echte iPhone-ATT-Schreibbefehle für Licht Ein/Aus/Dimmen beobachtet. Grow-Central-Replay weiterhin nicht freigegeben.
- Ventilator: Nutzer bestätigt, dass der Ventilator in Mars Legacy aktuell gekoppelt ist, aber ausgeschaltet bleibt. Frühere BLE-Advertising-Bezeichnung `MZ_MZF002_0_A0A3B35EFDC8` laut Screenshot; die Zuordnung zu DF150-M ist noch nicht hardwareseitig gesichert.
- Für den MZF002-Kandidaten wurden am Pi Service-UUID `83677baa-3eb8-4866-b6b6-96e5ed5cc48d`, Write-UUID `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d` und Notify-UUID `6f588463-f8f1-44f8-bdae-a1272a1b0f6e` ermittelt. **Gleiche GATT-UUIDs sind kein Beweis für gleiche Befehls-Payloads.**
- Von der ersten iPhone-HCI-PCAP (3.930.276 Bytes) gehören 12 von 13 Writes an Handle 0x002D eindeutig zur FC 3000. Im untersuchten ATT-Write-Payload wurde keine Ventilator-Gerätekennung gefunden. Ein unzugeordneter Write darf nicht als Lüfterbefehl eingestuft werden.

## Neue Messreihe

Eine getrennte HCI-Aufnahme auf Jens-PC mit `idevicebtlogger` wurde unter `JL1976/Grow-Central/FC3000-BLE/mars_legacy_lamp_fan_20261112.pcap` gestartet. Das iPhone wurde per USB erkannt, der Logger bestätigte die Verbindung.

**Wichtig:** Ein HCI-Log erfasst nur die Bluetooth-Verbindungen des iPhones. »Gekoppelt« im Sinne von in der App hinterlegt garantiert **nicht**, dass gerade eine aktive BLE-Verbindung zum ausgeschalteten Ventilator besteht. Keine Verbindung zum Ventilator erzwingen und keine Aktion automatisch ausführen.

Für den nächsten praktischen Test zuerst ausschließlich das Ventilator-Gerät in Mars Legacy öffnen, ohne Ein/Aus oder Geschwindigkeit zu ändern. Sofern bereits im ausgeschalteten Zustand eine Verbindung besteht, können wir Discovery, Status/Notifications und mögliche Statusabfragen im iPhone-HCI-Log beobachten. Falls keine Daten auftreten, ist das ein Messbefund und kein Grund für erfundene Schreibbefehle. Erst mit ausdrücklicher Nutzerfreigabe eine kontrollierte Stufenfolge am Ventilator ausführen.

## Architektur

- Getrennte Geräte-ID, BLE-Verbindungszustände, Rohdaten- und Decoder-Pipelines für Lampe und Ventilator.
- Ein zentraler Connection Manager begrenzt aktive Verbindungsversuche, respektiert exklusive Mars-Legacy-BLE-Verbindung und vermeidet automatische Reconnect-Stürme.
- Keine öffentliche Veröffentlichung von Roh-HCI-PCAPs oder Tokens; keine aktive Grow-Central-Steuerung bis gerätespezifischer Validierung.
- Die belegten FC3000-Steuerbefehle niemals automatisch an den Ventilator senden.


## Reale Lüfter-Stufenmessung über iPhone (2026-11-12, Abschluss)

Der Anwender hat nach dem Einschalten des MZF002 die Lüfterstufen 25 % → 50 % → 75 % → 100 % → Aus in Mars Legacy bedient. Die HCI-Aufzeichnung wurde auf Jens-PC beendet und die vollständig geschriebenen PCAP-Daten unter `JL1976/Grow-Central/FC3000-BLE/mars_legacy_lamp_fan_20261112.pcap` privat belassen. **2.729.859 Bytes**, **32.373 Pakete**, **266** identifizierte `MZF002`-Notifications.

Die iPhone-ATT-Notifications korrelieren zeitlich mit allen Stufenwechseln:

| Zeit (aus PCAP, UTC) | Feld 12 Status | Feld 13 Sollwert | Feld 21 Drehzahl (U/min) | Beobachtung |
|---|---:|---:|---:|---|
| 18:36:27 | 0 | 25 | 0 | Ausgangszustand |
| 18:37:45 | 1 | 25 | 0 | eingeschaltet, Motor läuft an |
| 18:37:57 | 1 | 25 | 820 | 25 % stabil |
| 18:41:57 | 1 | 50 | 820 | Sollwert auf 50 % |
| 18:42:06 | 1 | 50 | 2100 | 50 % |
| 18:42:09 | 1 | 75 | 2160 | Sollwert auf 75 % |
| 18:42:12 | 1 | 75 | 2660 | 75 % |
| 18:42:15 | 1 | 100 | 2660 | Sollwert auf 100 % |
| 18:42:21 | 1 | 100 | 3020 | 100 %, höchste beobachtete Drehzahl |
| 18:42:27 | 0 | 100 | 2980 | ausgeschaltet, Motor läuft noch aus |
| 18:42:30 | 0 | 100 | 0 | Motor steht |

**Feldzuordnung:** Index 12 = Ein/Aus-Status, Index 13 = Sollwert in Prozent, Index 19 = Temperatur °C, Index 20 = relative Feuchte %, Index 21 = reale Motordrehzahl. Nutzerseitige Referenz bei laufendem Gerät: 820 U/min, 17,1 °C, 52,4 % rF, 114,0 CFM, 50,0 Pa. Die ersten drei Werte wurden passend in Notifications beobachtet. **114,0 CFM und 50,0 Pa bleiben ohne belegte Payload-Feldzuordnung.** Nicht als gemessene BLE-Sensordaten ausgeben.

**Wichtig:** In diesem Capture wurden trotz Stufenwechseln **0 ATT Write Requests/Commands** erkannt. Die Lüfter-Sollwertänderungen wurden also zuverlässig in den Notifications sichtbar, der eigentliche Befehlsweg ist **weiterhin ungeklärt**. Es darf **nicht** angenommen werden, dass die für FC 3000 identifizierten On/Off-/Dim-Payloads für den Lüfter gelten. Potenzielle andere Nachrichtentypen, Richtungen und GATT-/API-Pfade benötigen eine gesonderte Analyse.

`scripts/mars_legacy_mzf002_telemetry.py` liest die bislang identifizierten MZF002-Statusfelder offline. Dieser Stand ist noch **keine Grow-Central-Liveanbindung**, insbesondere keine Schreibsteuerung. Roh-Captures bleiben lokal; Git enthält nur anonymisierte Befunde.

## Grow-Central-Backendintegration (2026-11-12)

Die reale MZF002-Statusstruktur ist im App-Code verfügbar:

- `app/mars_legacy_telemetry.py`: begrenzter, gerätefamiliengeprüfter Parser; nimmt ausschließlich vollständige MZF002-Nachrichten an; gibt Ein/Aus, Sollwert %, Ist-RPM, Temperatur °C und relative Feuchte aus. Sitzungstoken und Geräte-ID werden nicht ausgegeben.
- `app/mars_hydro_ble.py`: neuer authentifizierter `POST /api/mars-hydro/ble/observe-fan-telemetry`-Endpunkt für einen zuvor vom Pi erkannten MZF002-Kandidaten. Maximal 5 Sekunden passive Notify-Beobachtung nach lokalem GATT-Connect, maximal zwölf dekodierte Samples, keine BLE-Schreibbefehle.
- `tests/test_mars_legacy_telemetry.py`: drei synthetische Tests inklusive Offline-/Setpoint-Verhalten, Grenzwerten und Redaction; auf Jens-PC ausgeführt, **3/3 erfolgreich**. Backenddateien außerdem ohne Syntaxfehler kompiliert.

**Wichtige Betriebseinschränkung:** Die App auf dem iPhone kann gleichzeitig die einzige BLE-Verbindung zum Gerät belegen. Der neue Endpunkt ist als Implementierung im Git verifiziert, **nicht als erfolgreich auf dem Grow-Pi live getestete Verbindung**. Für einen realen Pi-Lesetest muss die Hersteller-App die BLE-Verbindung zum Lüfter freigeben; keine automatische Trennung oder eigenmächtige Steuerung. Die öffentliche Statusanzeige darf Offline-/Nicht-Erreichbar-Zustände nicht als Echtzeit-Messwerte ausgeben.

CFM und Pa bleiben `null`, bis ihre Herkunft und Semantik nachgewiesen sind. Die Firmware-Daten sind keine Freigabe für beliebige Setpoint-Writes.
