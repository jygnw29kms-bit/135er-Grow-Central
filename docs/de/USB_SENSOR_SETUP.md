# USB-Sensor in Grow Central einrichten

Der geführte Ablauf ist für **Seeed XIAO ESP32-C3 mit GC Soil / HW-390** vorgesehen.
Das USB-Datenkabel wird am **Raspberry Pi**, nicht am Browser-PC, angeschlossen.
GC zeigt passende USB-Kandidaten im Gerätebereich automatisch an. USB VID/PID
allein bestätigt den Boardtyp nicht; vor dem Flashen muss der Nutzer den
angeschlossenen XIAO ESP32-C3 ausdrücklich bestätigen. Andere ESP32-Modelle werden
von esptool vor Schreibbeginn abgewiesen; eine automatische Unterscheidung aller
Boards mit demselben ESP32-C3-Chip ist nicht möglich.

## Ablauf

1. **USB erkannt:** „Einrichten“ öffnen und „Angeschlossenen Sensor prüfen“ wählen.
   Ist die aktuelle GC-Firmware schon vorhanden, wird die signierte USB-Identität
   mit einer neuen Zufallsanfrage geprüft. Andernfalls folgt der Firmware-Schritt.
2. **Firmware installieren:** Board und Installation bestätigen. GC prüft das
   eingebettete Paket auf Modell, Version, SHA-256 und feste Flashbereiche und
   installiert Firmware 0.4.1 im aktuellen Quellstand (Original-Image 369: 0.4.0). Das USB-Kabel dabei nicht trennen. Bei manuellen
   Bootloader-Boards gegebenenfalls BOOT beim Anschließen halten und danach neu
   versuchen. GC führt kein `erase_flash` aus; NVS-Identität und Kalibrierung
   bleiben in ihren eigenen Speicherbereichen erhalten.
3. **WLAN einrichten:** SSID, WLAN-Kennwort und den erreichbaren LAN-Broker dieses
   Pi auswählen. GC erstellt beim ersten Bedarf eine eigene lokale CA, ein
   Serverzertifikat mit den lokalen Hostnamen/IP-Adressen und einen individuellen
   MQTT-Zugang. CA und Zugang werden direkt per USB an genau den geprüften Sensor
   übertragen. Private Schlüssel und MQTT-Kennwörter werden nicht an den Browser
   ausgegeben. WLAN-Kennwörter erscheinen nicht in Antworten oder Job-Protokollen.
   Die Verwaltung des Brokers kann seine bestehenden Verbindungen kurz neu starten.
4. **Verbindung prüfen:** GC fordert eine aktuelle signierte MQTT-Antwort an und
   vergleicht sie mit der USB-Identität. Falsche WLAN-Daten oder ein unerreichbarer
   Pi-Broker führen nicht zu einer erfolgreichen Aufnahme. „Vorhandene Verbindung
   prüfen“ kann die WLAN-Einrichtung bei bereits konfigurierten Sensoren überspringen.
5. **Name und Raum:** Sensorname und Raum/Growbox auswählen oder einen Raum anlegen.
   Die bewusste Aufnahme erlaubt erst jetzt produktive Raumdaten. Ein abgelehnter
   oder widerrufener Sensor muss zuvor in der Sperrliste ausdrücklich erneut
   freigegeben werden. Ein wechselnder Geräteschlüssel wird nicht stillschweigend
   angenommen. Bereits angenommene Sensoren behalten ihre Zuordnung.

Der Dialog kann während eines laufenden Schritts geschlossen werden; der Job läuft
auf dem Pi weiter. Beim Trennen des USB-Kabels oder Neustart des GC-Dienstes kann ein
Vorgang abbrechen. Danach den Sensor erneut prüfen; keine automatische Flash-
Wiederholung durchführen. USB-Erkennung ist im geöffneten Gerätebereich alle drei
Sekunden aktiv. Nicht angeschlossene Kandidaten werden nicht als verfügbar gezeigt.

## Lokale Dienste und Grenzen

Das passende neue Test-Image enthält pyserial, esptool, ein geprüftes Firmware-
Paket, die dialout-Berechtigung und `grow-central-provisioning.service`. Build 365
enthält diesen USB-Ablauf noch nicht. Bestehende Installationen benötigen die
entsprechende Aktualisierung; die Oberfläche meldet ein fehlendes Paket oder den
nicht verfügbaren lokalen Broker-Dienst.

Der privilegierte Broker-Dienst kommuniziert ausschließlich über einen lokalen
Unix-Socket mit dem GC-Dienst. Er erlaubt nur die Einrichtung des festen lokalen
MQTT-Brokers und von `gc-soil-xxxxxx`-Konten. Geräte dürfen nur ihre eigenen
Announcement-/State-/Availability-/Proof-Topics senden und ihre Challenge lesen.
Der anonyme Listener bleibt auf 127.0.0.1:1883 begrenzt; Sensoren verwenden TLS/8883.
CA, Konten und Serverzertifikat liegen unter
`/etc/mosquitto/grow-central-sensor-broker`. Private CA-/Kontodateien gehören root
und sind Modus 0600; Mosquitto liest nur die vorgesehenen Zertifikate, ACL und
Passworthashes. Bestehende manuelle Listener auf 8883 werden nicht überschrieben.

Bei einer geänderten Pi-IP erneut über USB einrichten: das Serverzertifikat wird
um aktuelle lokale Adressen ergänzt, die CA und das individuelle Kennwort bleiben
bestehen. Eine ablaufende CA wird nicht automatisch gewechselt, weil bereits
konfigurierte Sensoren der alten CA vertrauen. Systemzeit/NTP und die Erreichbarkeit
des gewählten Pi-LAN-Hosts müssen für TLS stimmen.

Dieses Software-Onboarding ersetzt keine elektrische Prüfung oder Substrat-
Kalibrierung. „Bereit“ bestätigt Identität, Verbindung und Zuordnung; gültige
Bodenfeuchtewerte hängen zusätzlich vom angeschlossenen Messfühler ab. Ein Image-
Userspace-Boot ist kein echter Kernelboot. USB-Reset, Flash, WLAN/TLS und Sensorwerte
müssen auf der Zielhardware geprüft werden. BLE-Provisionierung bleibt nicht implementiert.

## Hardwaretest

- Neues Image auf separater Testkarte starten; USB-Datenkabel direkt am Pi.
- Unbekanntes Board vor Installation prüfen, XIAO-C3 bestätigen.
- Flash und Wiedererkennung beobachten; beim Update Identität/Kalibrierung vergleichen.
- WLAN/TLS-Verbindung bestätigen und Name/Raum zuweisen; Sensorwerte prüfen.
- USB nach erfolgreicher Einrichtung trennen: Messwerte müssen weiter über WLAN kommen.
- Fehlerfälle: falsches WLAN, abgezogenes Kabel, fehlender Broker, falsches Board.
- Ablehnung/Widerruf und Neustart dürfen keine automatische Freigabe erzeugen.

## Aktueller bestätigter Stand

USB-Aufnahme, MQTT über TLS und Bodenfeuchte-Anzeige wurden auf einem Pi 4 mit Build 369 und Hotfixes bestätigt. Der CA-Transfer muss vollständig sein: aktuelles Backend sendet paketweise und prüft die gespeicherte PEM-Länge. Reale Kalibrierung und Neustart-/Dauertests bleiben offen. Siehe [Sensor-Anleitung](SOIL_SENSOR_GUIDE.md) und [Hardwarebefund](SENSOR_HARDWARE_TEST_2026-10-14.md).
