# USB-Erstinbetriebnahme eines Grow-Central-Sensors

Dieser Ablauf ist der verbindliche Produktionsweg für einen neuen **Seeed XIAO ESP32-C3 mit GC Soil / HW-390**. Der Sensor wird für die komplette Erstinbetriebnahme per Daten-USB direkt am Grow-Central-Raspberry-Pi angeschlossen. Erst nach allen Prüfungen darf er abgezogen, in den vorgesehenen Raum gebracht und in das Substrat eingesetzt werden.

## Verbindlicher Ablauf

1. **USB-Erkennung und Boardprüfung**
   Grow-Central erkennt nur unterstützte serielle USB-Kandidaten. Der Bediener bestätigt ausdrücklich den XIAO ESP32-C3. `esptool` prüft den tatsächlichen ESP32-C3 zusätzlich vor jedem Schreibvorgang.

2. **Firmware installieren oder prüfen**
   Grow-Central verwendet ausschließlich das zum Image gehörende, per Manifest und SHA-256 geprüfte Firmwarepaket. Ein neuerer Sensor wird niemals automatisch auf eine ältere gebündelte Firmware zurückgesetzt. Updates schreiben nur Bootloader, Partitionstabelle, OTA-Metadaten und Applikation; NVS wird nicht mit `erase_flash` gelöscht.

3. **Kryptografische Geräteidentität und Hardwarebindung**
   Nach dem Start fordert Grow-Central über USB einen frischen 256-Bit-Nonce-Proof an. Der Sensor signiert ihn mit seinem individuellen P-256-Langzeitschlüssel. Zusätzlich gehört die aus dem ESP32-C3-eFuse abgeleitete Hardware-UID zum signierten Datensatz. Grow-Central bindet zusammen:
   - Geräte-ID `gc-soil-xxxxxx`
   - P-256 Public Key / SHA-256-Fingerprint
   - eFuse-Hardware-UID
   - Modell und Firmwareversion

   Ändert sich während der Einrichtung Schlüssel oder Hardware-UID, wird der Ablauf sofort gesperrt. Ein bereits gespeicherter, abgelehnter oder widerrufener Sensor wird nicht stillschweigend wieder freigegeben.

4. **Pflichtkalibrierung am angeschlossenen Sensor**
   Ein Sensor wird ohne abgeschlossene Kalibrierung niemals als einsatzbereit markiert.
   - **Trockenreferenz:** Sensorfläche sauber und trocken in Luft halten, dann `CAL AIR` ausführen.
   - **Nassreferenz:** nur die Sensorfläche/Probe in die Referenz eintauchen; XIAO und Elektronik trocken halten, dann `CAL WATER` ausführen.
   - Grow-Central akzeptiert die Kalibrierung nur, wenn beide Punkte persistent im Sensor gespeichert sind und die Messspanne plausibel ist (`air_raw > wet_raw + 100`).

   `RESET CAL` setzt die Pflichtfreigabe wieder zurück. Danach muss die Kalibrierung vollständig wiederholt werden.

5. **WLAN und TLS-MQTT per USB einrichten**
   Erst nach erfolgreicher Kalibrierung erzeugt Grow-Central einen individuellen Brokerzugang. CA, MQTT-Zugang und WLAN-Daten werden direkt an genau den zuvor verifizierten USB-Sensor übertragen. Geheimnisse werden nicht an den Browser zurückgegeben und nicht in Audit-Logs geschrieben.

6. **Netzwerkidentität erneut beweisen**
   Der Sensor verbindet sich selbstständig mit WLAN und TLS-MQTT. Grow-Central fordert anschließend einen neuen Nonce-Proof über MQTT an. Der Proof muss denselben Langzeitschlüssel und dieselbe Hardware-UID wie die USB-Prüfung tragen. Außerdem muss die Firmware weiterhin eine abgeschlossene Kalibrierung melden.

7. **Name und Raum bewusst festlegen**
   Erst jetzt werden Sensorname und Raum/Growbox ausgewählt. Die Oberfläche verlangt eine zusätzliche ausdrückliche Bestätigung, dass **dieser physische Sensor** zum ausgewählten Raum gehört. Ohne diese Bestätigung gibt es keine produktive Raumzuweisung.

8. **Finaler Einsatzbereit-Check**
   Vor `READY` prüft Grow-Central noch einmal:
   - identischer Public Key/Fingerprint
   - identische eFuse-Hardware-UID
   - Kalibrierung vollständig und plausibel
   - TLS-MQTT-Verbindung aktiv
   - frischer Netzwerk-Proof
   - `sensor_ok = true`
   - Signalqualität mindestens `FAIR`
   - Name und Raum gespeichert

   Erst danach lautet der Status **Einsatzbereit**. Jetzt darf der Sensor vom USB getrennt, in den zugewiesenen Raum gebracht und mit der Sensorfläche in das Substrat eingesetzt werden.

## Sicherheitszustände

Ein neu erkannter Sensor bleibt bis zum Abschluss `DISCOVERED`. Produktive Raumdaten werden ausschließlich von `TRUSTED`-Sensoren angenommen. `REJECTED` und `REVOKED` bleiben persistent gespeichert und werden durch erneutes Anstecken oder Rediscovery nicht automatisch aufgehoben.

## Clone-/Vertauschungsschutz

Der aktuelle XIAO-Schutz kombiniert physischen USB-Besitz, frische Nonces, den individuellen P-256-Schlüssel, den öffentlichen Fingerprint und die eFuse-Hardware-UID. Damit werden versehentliche Vertauschungen sowie ein kopierter Geräteschlüssel auf anderer unveränderter Hardware erkannt.

Das ist noch kein Schutz gegen einen Angreifer mit vollständiger physischer Kontrolle, der Firmware und Flashinhalt gezielt extrahiert und manipuliert. Für diesen höheren Schutzgrad sind später Secure Boot, Flash-/NVS-Verschlüsselung oder ein externer Secure Element erforderlich. Grow-Central behauptet deshalb keine absolute Hardware-Unklonbarkeit.

## Kalibrierungsbedeutung

Die AIR-/Nassreferenz ist eine technische relative Feuchteskala und keine bestätigte volumetrische Wassergehaltsmessung. Sie macht den Sensor für Grow-Central reproduzierbar einsatzfähig. Substratabhängige Feinprofile können später ergänzend eingeführt werden, ohne die sichere Erstaufnahme zu ersetzen.

## Serverseitiger Kalibrierungsnachweis

Zusätzlich zu den im Sensor gespeicherten Referenzpunkten führt Grow-Central einen eigenen Calibration Record unter /var/lib/135er-grow-central/sensor-calibration.db. Der Record bindet die Kalibrierung an Geräte-ID, Public Key/Fingerprint, eFuse-Hardware-UID, Firmwareversion und Capability. Er enthält AIR-/Nassreferenz, RAW-Span, Qualitätsdaten, Kalibrierzeitpunkt, Schema sowie Gültigkeits- und Invalidierungsgrund.

Bodenfeuchte-Prozentwerte werden produktiv nur verwendet, wenn dieser Record gültig ist **und** der aktuelle signierte Live-Proof dieselbe Identität, Hardware-UID, Firmware und eine weiterhin aktive Sensor-Kalibrierung bestätigt. Bei Key-, Hardware- oder Firmwarewechsel wird der Record ungültig; die UI zeigt dann Kalibrierung erforderlich statt einen vermeintlich gültigen Prozentwert.

Die Final-Master-Navigation enthält dafür den eigenen Punkt **Sensor-Kalibrierung**. Dort werden reale Sensoren, Raum, Onlinezustand, Firmware, gekürzter Fingerprint, Kalibrierzeitpunkt, Qualitätsdaten und Grund für eine erforderliche Kalibrierung angezeigt. Schreibende Kalibrieraktionen bleiben auf den begrenzten USB-Onboarding-Pfad beschränkt.

## BLE

BLE bleibt in Firmware 0.5.x als verschlüsselter Recovery-/Servicepfad erhalten. Es ist **nicht mehr der primäre Produktionsweg für die Erstaufnahme eines neuen Sensors**. Ein neuer Sensor wird zuerst vollständig über USB identifiziert, kalibriert, provisioniert und einem Raum zugeordnet.

## Verhalten nach der Freigabe

Nach `Einsatzbereit` arbeitet der Sensor autonom weiter. WLAN- oder MQTT-Ausfall stoppt die Messung nicht. Nach erfolgreicher Verbindung sendet er signierte Messwerte und beantwortet frische Identitäts-Challenges. Eine spätere Änderung von Hardware-ID oder Geräteschlüssel führt nicht zu stiller Wiederaufnahme.
