# Sensor TLS-Diagnose 0.4.1

Der Hardwaretest mit Firmware 0.4.0 erreicht den Broker auf 8883, bricht aber vor MQTT CONNECT ab. Broker TLS 1.2, CA-Verifikation und IP-SAN bestehen den OpenSSL-Test. Die aktuelle CA wurde per USB gespeichert; der Fehler bleibt. Eine definitive Ursache ist noch nicht festgestellt.

Firmware 0.4.1 erhöht den TLS-Handshake-/Socket-Timeout von 2 auf 10 Sekunden und den MQTT-Timeout von 1500 auf 5000 ms. Bei einem Verbindungsfehler wird der konkrete Mbed-TLS-Code samt Text und UTC-Epoch ausgegeben. NET INFO enthält ebenfalls UTC-Epoch und CA-Länge. Keine Passwörter, privaten Schlüssel oder CA-Inhalte werden ausgegeben. TLS-Validierung bleibt erforderlich.

`scripts/apply-sensor-tls-diagnostics.py` lädt das gepinnte Kandidatenpaket und den passenden USB-Backendcode, prüft SHA256, Manifest, Offsets und Syntax, sichert die Installation und stellt das Paket für den USB-Assistenten auf Build 369 bereit. Es flasht nicht automatisch. Bei fehlgeschlagener Validierung oder fehlgeschlagenem Dienststart wird zurückgerollt. Es benötigt den bisherigen UI-/USB-Hotfix; unbekannte lokale Änderungen werden nicht überschrieben.

Nach Installation: Browser neu laden, Sensor über USB einrichten, XIAO ESP32-C3 bestätigen und Firmware installieren. Kein erase_flash. NVS mit Identität, Kalibrierung und WLAN-/MQTT-Daten bleibt erhalten. Danach vorhandene Verbindung prüfen; sofern nötig WLAN mit der LAN-IP des Pi erneut einrichten. Bei einem weiteren Fehler NET INFO über das bekannte USB-Diagnoseskript lesen; die neuen GC_NET tls_error-Zeilen und utc_epoch zur Diagnose senden.

Validierung: PlatformIO-Build erfolgreich, Firmware 897106 Byte Programmspeicher (68,4 %), RAM 40500 Byte (12,4 %). USB-Onboarding-Regressionen und Installer-Rollback getestet. Download/Archiv-Prüfsummen online geprüft. Tatsächlicher MQTT-Erfolg und echte Firmwareinstallation auf dem Pi bleiben bis zum Hardwaretest unbestätigt. Das veröffentlichte Image 369 wird nicht ersetzt.

## Hardwarebefund nach USB-Übertragung

Auf dem Nutzer-Pi meldete 0.4.1 `ca_bytes=307` und `tls_error=-8576` (ungültiges X509-Format). Die aktuelle Broker-CA benötigt als PEM 554 Bytes. Nach Übertragung der identischen CA in 32-Byte-Paketen mit 30 ms Abstand meldete der Sensor `ca_bytes=554`, `mqtt_online` und wiederholt `mqtt_connected=yes`. Der abgeschnittene USB-Transfer ist damit als Ursache dieses Fehlers bestätigt. WLAN-/Raumzuweisung und die abschließende signierte Aufnahme sind separat zu prüfen.

Der aktuelle Backendcode sendet USB-Kommandos in solchen Paketen und prüft nach der CA-Bestätigung per NET INFO die gespeicherte PEM-Länge. Ein abgeschnittener Transfer kann nicht mehr nur durch `OK broker CA stored` den nächsten Einrichtungsschritt erreichen. Dieser zusätzliche Schutz ist im Git-Quellstand; der bereits installierte, zuvor gepinnte 0.4.1-Installer enthält ihn noch nicht. Der momentan verbundene Sensor benötigt keine erneute Provisionierung.
