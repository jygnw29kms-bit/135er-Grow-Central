# Bodensensor: realer Hardwarebefund vom 14. Oktober 2026

## Umfang und Belege

Getestet wurde eine Nutzerinstallation auf Raspberry Pi 4 Model B mit Image Build 369, Seeed XIAO ESP32-C3, HW-390 und Firmware 0.4.1 nach den In-place-Hotfixes. Grundlage sind vom Nutzer bereitgestellte Terminalausgaben und Rückmeldungen. Es bestand kein direkter SSH-Zugriff aus der Cloud-Umgebung. Personenbezogene Diagnosedaten, Gerätefingerabdrücke, Netzwerkzugänge und private Schlüssel werden nicht veröffentlicht.

| Prüfung | Befund |
|---|---|
| Sensor-Messung per USB | Messwerte und Qualitätsdiagnose vorhanden |
| WLAN | verbunden, Signal etwa −69 bis −71 dBm im letzten Test |
| Pi-Broker TLS 1.2 | OpenSSL-Verifikation erfolgreich |
| Sensor-Firmware 0.4.1 | Version im seriellen Log bestätigt |
| CA-Transfer | zunächst 307 statt erwarteter 554 PEM-Bytes; X509-Formatfehler −8576 |
| Paketweise CA-Übertragung | 554 Bytes gespeichert; `mqtt_online` und mehrfach `mqtt_connected=yes` |
| Aufnahme und Raumzuordnung | Nutzer bestätigt: Sensor aufgenommen |
| Bodenfeuchte-Historie | nach UI-Hotfix vom Nutzer als funktionierend bestätigt |
| Kalibrierung / Substratgrenzen | noch nicht durchgeführt bzw. bestätigt |
| USB abziehen / Neustart / Langzeitbetrieb | separate Prüfung offen |
| Gesamtes Universal-Image / andere Pi-Klassen | nicht vollständig validiert |

## Korrekturen im aktuellen Quellstand

1. Mosquitto-Drop-in dupliziert keine globalen Persistence-Einstellungen mehr.
2. USB-Sensoren bleiben sichtbar; Zustimmung ersetzt die manuelle Hex-Eingabe, frische signierte Identitätsprüfung bleibt erforderlich.
3. Der Assistent bevorzugt die LAN-IP des Pi; `.local` wird für den Sensor-Broker abgelehnt.
4. Broker-Zertifikate enthalten reguläre IP-SANs und exakte DNS-SANs für dieselben IPs zur ESP32-Kompatibilität. Keine Abschaltung der TLS-Verifikation.
5. Firmware 0.4.1 liefert TLS-Fehler, UTC und CA-Länge; längere Verbindungsfristen.
6. USB-Übertragung erfolgt in 32-Byte-Paketen; der Backendcode prüft die gespeicherte PEM-Länge nach der Bestätigung.
7. Bodenfeuchte erhält eine eigene Kachel und Historienspalte, getrennt von Luftfeuchte.

Die original veröffentlichte Image-Datei Build 369 wird nicht nachträglich verändert. Hotfixes und ein neuer vollständiger Image-Build bleiben nachvollziehbar getrennt.
