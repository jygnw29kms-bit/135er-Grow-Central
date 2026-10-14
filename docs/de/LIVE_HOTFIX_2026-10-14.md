# Live-Hotfix für Build 369

Der physische Pi-Test meldete einen Mosquitto-Fehler: die Debian-Hauptkonfiguration
enthält bereits globale Persistence-Einstellungen. Die zusätzliche
persistence_location im Grow-Drop-in verhinderte den Start. Der Quell-Build ist
korrigiert; der native Mosquitto-Test nutzt nun die tatsächliche Image-Konfiguration
zusammen mit Debians globalen Einstellungen. Künftige Image-Boot-/Reboot-Gates
verlangen auch aktive Mosquitto- und Provisioning-Dienste.

Die aktuelle UI blendete per USB erfasste Sensoren aus der normalen Sensorliste
aus. Nach Abziehen erschienen gespeicherte Einträge wieder, ohne dass das frische
Erreichbarkeit bewies. Neue UI: Eintrag bleibt sichtbar, angeschlossenes USB wird
gekennzeichnet und „USB-Einrichtung fortsetzen“ öffnet den passenden Assistenten.
Netzwerkeinträge werden als gespeicherte Identitäten bezeichnet; Aufnahme benötigt
weiterhin eine aktuelle Identitätsantwort. Kein stromloser Sensor gilt als bereit.

Die manuelle Hex-Eingabe entfällt in der UI. USB-Aufnahme bleibt an frische USB-
und Netzwerk-Nachweise gebunden. Bei reiner Netzwerkaufnahme wird der vollständige
angezeigte Fingerabdruck automatisch an die ausdrücklich bestätigte Aufnahme
gebunden; der Nutzer vergleicht ihn am Sensor. Geänderte Schlüssel/Sperren werden
weiter abgewiesen. Das bestehende 16-Zeichen-API-Format bleibt für alte Clients
kompatibel; es gibt keine automatische Annahme.

Supportdownloads pinnen die tatsächliche Archivdatei statt den wechselnden
latest-Symlink. Cache-Verwendung wird unterbunden. Die UI lädt mit aktiver Session,
zeigt HTTP-/Übertragungsfehler und bietet Diagnose im Browser zum Kopieren an.
„Datei unvollständig“ ist keine bestätigte Chrome-Sicherheitsblockade. Netzwerk-/
Proxy-/Pi-spezifische Abbrüche müssen auf der laufenden Installation erneut geprüft
werden. MQTT- und Provisioning-Journale sind jetzt im Diagnosesnapshot enthalten.

## Installationsweg

`scripts/apply-grow-ui-hotfix.py` aktualisiert ausschließlich sechs getestete
Python-/JS-Dateien im bestehenden Build 369. Es prüft gepinnte SHA256-Werte,
sichert bestehende Dateien, bewahrt unerkannte lokale Änderungen, startet nur
Grow Central neu und stellt bei fehlgeschlagenem Start die alten Dateien wieder
her. Zugangsdaten, Datenbanken, Sensorzuordnungen und Firmware werden nicht geändert.
Bereits gleicher Hotfix ist idempotent. Build-Anzeige bleibt 369.

`--check-only` lädt/verifiziert/kompiliert die Dateien ohne Installationsänderung.
Kein direkter Pi-Zugriff besteht aus der aktuellen Cloud-Sitzung. Der Nutzer muss
den Installer in seiner bestehenden SSH-Sitzung ausführen. Danach Strg+F5 und den
angeschlossenen Sensor über die USB-Einrichtung prüfen. Ohne passende Zugänge und
frischen Netzwerk-Nachweis erfolgt keine erfolgreiche Aufnahme.

Der Hotfix-Installer behebt die sechs UI/API-Dateien; er verändert keine laufende
Mosquitto-Konfiguration. Die separat angewandte Persistence-Korrektur muss zuvor
`systemctl is-active mosquitto` mit `active` beantworten.

## Ergänzungen aus dem MQTT-Hardwaretest

Die vollständige CA benötigt in der getesteten Installation 554 PEM-Bytes. Ein abgeschnittener USB-Transfer speicherte nur 307 Bytes und wurde von Firmware 0.4.0/0.4.1 zunächst dennoch als gespeichert bestätigt. Paketweise Übertragung stellte MQTT her. Der aktuelle Backendcode prüft zusätzlich die gespeicherte Länge. Die erfolgreiche Verbindung und Bodenfeuchte-Anzeige sind vom Nutzer bestätigt.

Für eine unveränderte Build-369-Baseline gilt folgende Reihenfolge:

1. Mosquitto-Persistence-Korrektur anwenden und Broker auf `active` prüfen.
2. UI-/USB-Hotfix über [`apply-grow-ui-hotfix.py`](../../scripts/apply-grow-ui-hotfix.py) installieren.
3. Broker-Zertifikatskompatibilität über [`apply-mqtt-tls-hotfix.py`](../../scripts/apply-mqtt-tls-hotfix.py) aktualisieren; CA bleibt erhalten.
4. [`apply-sensor-tls-diagnostics.py`](../../scripts/apply-sensor-tls-diagnostics.py) stellt Firmware 0.4.1 und den passenden Backendcode mit CA-Transferschutz bereit. Nur bei älterer Sensorfirmware im USB-Assistenten flashen.
5. Bodenfeuchte-Anzeige über [`apply-soil-display-hotfix.py`](../../scripts/apply-soil-display-hotfix.py) aktualisieren und Browser mit Strg+F5 neu laden.

Bereits funktionierende, aktualisierte Installationen benötigen keine erneute Aufnahme und keinen erneuten Flash. Den alten UI-Hotfix nicht nach dem Firmware-/Backend-Update anwenden: gepinnte Altinstaller akzeptieren neuere lokale Dateien absichtlich nicht. Alle Installer verweigern unbekannte lokale Änderungen und prüfen ihre Downloads. Das Original-Image 369 bleibt unverändert.
