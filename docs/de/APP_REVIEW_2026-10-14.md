# Grow Central — erneute Prüfung vom 14. Oktober 2026

Der aktuelle Entwicklungsstand enthält die lokalen Grow-Funktionen, Räume,
Pflanzen und Tagebuch, unterstützte Gerätepfade, Kamera-/Energieüberwachung,
optionalen Cloud-Link, native Sensoraufnahme und Home-Assistant-Export.
Der Quellstand basiert auf dem erfolgreich gebauten USB-Candidate 368 und
berücksichtigt den danach geprüften Upstream-Stand.

## Sensoraufnahme und Interface

USB-Kandidaten erscheinen im Gerätebereich. Der Assistent führt durch Erkennung,
signierte Identitätsprüfung, bestätigtes Firmware-Flashen, WLAN/MQTT-TLS,
Netzwerk-Nachweis sowie Name/Raum und Aufnahme. Firmwarepaket 0.4.0 wird separat
gebaut und mit Hash/Offsets geprüft. Unterstützt ist XIAO ESP32-C3 mit HW-390.
Andere Boards werden nicht automatisch geflasht. Ablehnung, Widerruf und
Schlüsselwechsel bleiben bewusst manuell; abgespeicherte Sperren gelten weiter.

Der lokale Brokerhelper richtet CA, Serverzertifikat und individuelle,
topic-begrenzte Accounts ein. Zugangscodes und WLAN-Passwörter erscheinen nicht
in öffentlichen API-Antworten/Audit. Geräteeinsatz setzt aktuellen Identitätsnachweis
und bewusste Zuordnung voraus. Automatische BLE-Einrichtung ist nicht umgesetzt.
Details: [USB-Sensoraufnahme](USB_SENSOR_SETUP.md).

## Apple, Android und Home Assistant

Die installierbare HA-Komponente stellt ausdrücklich freigegebene Sensoren und
Schalter bereit, mit getrenntem API-Schlüssel und ohne Rückexport-Schleifen.
Apple Home/Siri, Alexa und Google verwenden die dokumentierten HA-Brücken.
HA läuft separat; der Pi-Candidate installiert keinen kompletten HA-Server.
Kontokopplung und Sprachbefehle erfordern Prüfung auf der Zielinstallation.
Details: [Home Assistant](HOME_ASSISTANT.md).

## Prüfungen und Build

303 bestehende Backend-/Integrationsprüfungen erneut bestanden, einschließlich
realer Mosquitto-TLS-, Zertifikats-/ACL- und USB-PTY-Prüfungen. Drei zusätzliche
Projektgrenzen-Prüfungen sperren fremde Printer-Artefakte/Runtime-Integrationen,
lassen die eigenen Grow-Kameras aber zu. Die Domainprüfung wurde mit drei weiteren Regressionstests auf Grow-Adressen
und exakt erlaubte externe Downloads geprüft. Insgesamt 309 Python-Tests bestanden.
Je acht Prüfungen der installierbaren Home-Assistant-Komponente gegen HA 2025.1.4
und 2026.10.1 in echter HA-Testlaufzeit bestanden. Abhängigkeiten
zeigen keine Konflikte. Firmware-, Sicherheits-, Syntax-, Boot/Reboot- und
Pristine-Prüfungen bleiben Teil des neuen Image-CI.

Zentraler Release-Status und README nennen nach erfolgreicher Veröffentlichung
den bereinigten Candidate 369. Image, Firmware und HA-Paket referenzieren denselben
Quellstand; veröffentlichte Prüfsummen wurden kontrolliert.

## Grenzen

Keine neue physische Pi-/USB-/BLE-/Geräteprüfung in dieser Cloud-Sitzung.
Kein Firmware-Flash oder Update am Nutzer-Pi durchgeführt. Ressourcen-, Strom-,
Kamera-, Funk-, Sensor- und Sprachassistentenpfade auf echter Hardware validieren.
Ein bestandener Software-/Image-Test macht keinen Stable-Release.
