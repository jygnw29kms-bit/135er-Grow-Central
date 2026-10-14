# Grow-Central-Bodensensor einrichten und kalibrieren

## Hardware und Messgrenzen

Der derzeitige USB-Flashpfad unterstützt **Seeed XIAO ESP32-C3 / HW-390**, Firmware **0.4.1** im aktuellen Quellstand. Der HW-390 liefert einen kapazitiven Feuchte-Referenzwert. Er misst weder Temperatur noch Luftfeuchte, pH oder EC/Nährstoffgehalt. Dafür sind zusätzliche Sensoren erforderlich.

Die Prozentzahl ist ohne Substratkalibrierung kein exakter volumetrischer Wassergehalt. Salzgehalt, Substrat und Einstecktiefe beeinflussen die Messung. Ein angezeigtes `AIR_DRY` beschreibt den Firmwarezustand anhand der Referenzen; es ersetzt keine Bewertung des konkreten Substrats.

## Einrichtung

1. Sensor per Daten-USB am Pi anschließen und in Geräte > USB-Sensor einrichten öffnen.
2. XIAO ESP32-C3 bestätigen und nur bei Bedarf die geprüfte Firmware installieren. USB während des Flashens angeschlossen lassen. Kein `erase_flash`: Identität, Zugangsdaten und Kalibrierung bleiben in NVS erhalten.
3. WLAN einrichten, den Pi als lokalen MQTT-Broker über dessen **LAN-IP** wählen. Der Assistent erzeugt Zertifikat und individuellen Sensorzugang. Keine `.local`-Adresse für den Sensor verwenden.
4. Eine bestehende Verbindung mit „Sensor hat bereits eine Verbindung – prüfen“ prüfen. Erfolgreiches WLAN allein ist noch keine bestätigte MQTT-Verbindung.
5. Gerätename und Raum zuweisen; Aufnahme ausdrücklich bestätigen. Die frische signierte Identität bleibt Pflicht.
6. Raum > Sensordaten > **MESSWERTE JETZT**. Bodenfeuchte wird getrennt von Luftfeuchte angezeigt. Standardmäßig werden Raumwerte alle fünf Minuten erfasst; mehrere zugeordnete Bodenfühler werden zum Raum-Mittelwert zusammengefasst.

## Zweipunkt-Referenzkalibrierung per USB

Die Firmware unterstützt folgende serielle Befehle bei **115200 Baud**. Den USB-Einrichtungsdialog schließen und keine parallelen seriellen Werkzeuge verwenden.

| Befehl | Vorgehen |
|---|---|
| `CAL AIR` | Messsonde reinigen, vollständig trocknen, frei in die Luft halten und ruhig halten. Trockenreferenz speichern. |
| `CAL WATER` | Nur den dafür vorgesehenen Messbereich ins Wasser halten und stabilisieren lassen. Elektronik, Anschlüsse und USB bleiben trocken. Nassreferenz speichern. |
| `INFO` | Gespeicherte Werte `air_raw` und `water_raw` prüfen. |
| `RESET CAL` | Auf vorläufige Werkreferenzen zurücksetzen. |

Die Werte werden dauerhaft auf dem Sensor gespeichert. Ein komfortabler Kalibrierungsdialog ist noch nicht implementiert. Bei nicht eindeutig abgegrenztem oder ungeschütztem Messbereich die Sonde nicht eintauchen; zuvor die konkrete Hardwareausführung prüfen.

## Grenzwerte im verwendeten Substrat

Nach der Referenzkalibrierung dieselbe Einstecktiefe und Position verwenden. Den Wert am gewünschten trockenen Gießpunkt und nach vollständigem Gießen und Abtropfen protokollieren. Daraus entstehen substratspezifische Grenzwerte. Keine pauschalen Prozentgrenzen ohne diese Prüfung für automatische Bewässerung übernehmen. Der reale Kalibrierungstest dieser Installation ist noch offen.

## Vorhandene Diagnosewerte

Die signierte Telemetrie liefert Roh-/Median-/Filterwerte, Min/Max, Streuung, Qualität, Messzustand, Trocken-/Nassreferenz, WLAN-Signalstärke, Laufzeit und Firmware. Die Raumhistorie zeigt aktuell den Feuchte-Mittelwert; eine separate Diagnoseansicht ist noch nicht implementiert.

Bei MQTT-Problemen `NET INFO` lesen: `wifi_status=3`, eine IP und `mqtt_connected=yes` zeigen eine bestehende Verbindung. Firmware 0.4.1 meldet zusätzlich UTC-Epoch, `ca_bytes` und bei Fehlern `tls_error`. Ein `OK broker CA stored` allein garantiert bei alter Firmware keinen vollständigen Transfer. Keine Zertifikatsprüfung abschalten; [Hardwarebefund](SENSOR_HARDWARE_TEST_2026-10-14.md) beachten.
