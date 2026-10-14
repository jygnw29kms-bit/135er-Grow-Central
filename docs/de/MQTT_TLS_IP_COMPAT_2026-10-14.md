# MQTT-TLS und ESP32-IP-Ziele

Physischer Test: WLAN verbunden, richtige Broker-IP, TCP am Pi angekommen,
Broker beendet die Verbindung vor MQTT-CONNECT. Zertifikatszeit und IP-SANs
waren korrekt. Firmware 0.4.0 baut mit ESP32 Arduino/Mbed TLS 2.28.7.

Mbed TLS 2.28.7 `x509_crt_check_san()` prüft nur dNSName, nicht iPAddress:
https://github.com/Mbed-TLS/mbedtls/blob/v2.28.7/library/x509_crt.c

Nativ gegen offiziellen 2.28.7-Quellstand getestet: bisheriges Zertifikat mit
IP-SAN und .local-DNS-SAN ergibt -9984 / flags 0x4 (CN_MISMATCH). Ergänzt man
exakt dieselbe zulässige IP als dNSName, besteht die Prüfung mit 0 / flags 0.
Ein anderes IP-Ziel wird weiterhin abgewiesen. Moderne Clients behalten die
regulären iPAddress-SANs und die CA-/Signaturprüfung.

Der Brokerhelper stellt alte Serverzertifikate einmal kompatibel neu aus;
die vorhandene CA bleibt erhalten. Individuelle Kennwörter, ACL, Geräteidentität,
Kalibrierung und Firmware werden nicht geändert. Wiederholter Aufruf nutzt das
bereits passende Zertifikat. Dies ist ein Interoperabilitätspfad für den alten
TLS-Client, keine abgeschaltete Namens- oder Zertifikatsprüfung.

`scripts/apply-mqtt-tls-hotfix.py` installiert den gepinnten Helper für Build 369,
sichert Code/Serverzertifikat/Serverschlüssel in rootgeschütztem Backup,
prüft unveränderte CA und gültige Zertifikatskette, startet beide Dienste neu
und stellt bei Fehlern alte Dateien wieder her. Kein Flash nötig. Direkter
Pi-Zugriff besteht aus der aktuellen Cloud-Sitzung nicht; lokal ausführen.

318 Python-Tests einschließlich realem Broker/TLS, Legacy-Zertifikatsmigration,
CA-Persistenz und idempotenter Neuausstellung bestanden. Die anschließende
Sensor-Wiederverbindung muss auf dem tatsächlichen Pi bestätigt werden.
