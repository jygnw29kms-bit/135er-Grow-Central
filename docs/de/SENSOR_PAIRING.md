# Native Sensoraufnahme · 13. Oktober 2026

> **Produktionsregel ab Firmware 0.5.1:** Die Erstaufnahme eines neuen Soil-Sensors ist USB-first. Der Sensor bleibt bis zur vollständigen Firmware-/Hardwareidentitätsprüfung, Pflichtkalibrierung, TLS-MQTT-Prüfung sowie bestätigter Name-/Raumzuweisung `DISCOVERED`. Erst der finale Check setzt `TRUSTED`/`Einsatzbereit`. BLE bleibt Recovery-/Servicepfad und ist nicht mehr der primäre Erstaufnahmeweg. Der genaue Ablauf steht in [USB_SENSOR_SETUP.md](USB_SENSOR_SETUP.md).

Die Vorgaben stammen aus dem vom Nutzer geteilten [Chat](https://chatgpt.com/share/6ace61d2-cc28-83eb-bab0-7651912da6d1). Der Remote-Stand `1cef7d9` enthält bereits HW-390/XIAO-Bodenfeuchte, MQTT, Raumzuordnung und Substratanzeige. Die hier ergänzte Änderung betrifft die manuelle Vertrauensentscheidung und deren Durchsetzung. Touran-Code bleibt unberührt.

## Implementierter Ablauf

1. Ein dauerhaft laufender MQTT-Beobachter erkennt native Ankündigungen; Discovery funktioniert unabhängig von einem geöffneten Browser. Alte, unsignierte Firmware wird nur als nicht aufnahmefähiger Kandidat angezeigt.
2. Die Oberfläche zeigt **Neu – Entscheidung offen**. Der Nutzer entscheidet **Annehmen** oder **Ablehnen**; keine automatische Aufnahme, Ablehnung oder Raumzuordnung.
3. Bei Annahme: eigenen Namen eingeben, Raum/Growbox auswählen oder ausdrücklich anlegen, die letzten **16 Hex-Zeichen** des vollständigen Sensor-Fingerabdrucks mit `GC_ID fingerprint` am physischen Sensor vergleichen und eingeben.
4. Erst beim letzten Klick fordert GC einen neuen, zufälligen 256-Bit-Nonce an. Der Sensor muss ihn mit seinem individuellen Schlüssel signiert bestätigen. Retained/alte Antworten genügen nicht.
5. Erst nach dieser Prüfung und gespeicherter Raumzuweisung erhält er **TRUSTED**. Produktive Messwerte und Online-Status erfordern ebenfalls aktuelle signierte Nonce-Antworten.
6. **REJECTED** und **REVOKED** bleiben in SQLite erhalten und erzeugen bei Rediscovery keine neue Meldung. Der Nutzer kann sie wieder zur Entscheidung freigeben; daraus entsteht noch kein Vertrauen.

Der Flow ist in Desktop-, Mobile- und Legacy-Oberfläche vorhanden; die produktive Console verwendet die Legacy-Seite im iframe. Benachrichtigungen führen zur Geräteansicht. Änderungen erfordern die vorhandene GUI-Sitzung oder den lokalen API-Token. Native Daten gelangen ohne TRUSTED nicht in die Raumansicht oder Raumhistorie. Native Schreibbefehle bleiben im neuen Pairing-Pfad vollständig gesperrt; bestätigte Aktorprotokolle benötigen eine eigene Freigabepolitik.

## Geräteidentität und Replay-Schutz

Firmware **0.5.2** erzeugt bzw. bewahrt ein individuelles P-256-Schlüsselpaar im NVS und bindet zusätzlich die aus dem ESP32-C3-eFuse abgeleitete Hardware-UID in die signierte Geräteankündigung ein. Hardware-Entropie wird zur Erzeugung aktiviert und vor ADC-Messungen wieder deaktiviert. Der private Schlüssel wird nicht über API oder serielle Diagnose ausgegeben. Seine Speicherung ist noch **nicht** gegen physische Flash-Auslese geschützt; Secure Boot/Flash-/NVS-Verschlüsselung sind nicht eingerichtet.

Envelope:

```json
{
  "schema": "gc-signed-v1",
  "algorithm": "ecdsa-p256-sha256",
  "public_key": "base64 DER SubjectPublicKeyInfo",
  "message": "genau signierter UTF-8-JSON-String",
  "signature": "base64 DER ECDSA-Signatur"
}
```

`message` enthält `device_id`, `kind`, `seq` und `body`. Die Signatur umfasst genau die UTF-8-Bytes dieses Strings, ohne nachträgliche JSON-Kanonisierung. Der öffentliche Schlüssel wird nach normalisiertem DER mit SHA-256 identifiziert. Nachrichten sind an ID, MQTT-Topic und Typ gebunden. SQLite speichert Sequenzen/Digests; ältere Sequenzen oder veränderte Inhalte mit derselben Sequenz werden zurückgewiesen. Identische Retained-Ankündigungen sind idempotent. Proofs tragen zusätzlich die aktuelle, einmalige GC-Nonce und werden niemals retained veröffentlicht.

Firmware reserviert Sequenzblöcke im NVS, um Reboots sicher zu überstehen, ohne für jede Messung Flash zu schreiben. Ein fremder Schlüssel mit derselben ID ersetzt den gespeicherten Schlüssel nicht. Nach vollständigem Factory-Reset muss der Nutzer die bisherige Identität ausdrücklich zurücksetzen: nur nach Ablehnung/Widerruf, mit Bestätigung der alten Fingerabdruck-Endung. Der alte Schlüssel wird dauerhaft gesperrt, alte Sequenzen werden entfernt, der neue Schlüssel muss neu erkannt und angenommen werden. `NET CLEAR` bewahrt Identität und Kalibrierung.

`GC_DEVICE_TRUST_DB` legt den Speicherort fest (Standard `/var/lib/135er-grow-central/device-trust.db`, Modus 0600). Diese Datei inklusive relevanter SQLite-Dateien muss bei Updates/Backups erhalten bleiben. Bereits zugewiesene Sensoren werden **nicht automatisch als vertrauenswürdig migriert**. Alte Raumhistorie bleibt erhalten; neue native Messungen erfordern Aufnahme und Firmware 0.3.0.

## MQTT und lokale Inbetriebnahme

Die Pi-Image-Konfiguration öffnet anonymes MQTT nicht mehr im LAN: Port 1883 bindet nur an `127.0.0.1`, die LAN-Firewallfreigabe betrifft 8883. Der Loopback-Listener bleibt für lokale Entwicklung zugänglich. Ein produktiver TLS-Listener wird erst mit tatsächlichen Zertifikaten, individuellen Passwortdatei-Einträgen und ACL eingerichtet. Die Vorlagen sind in `deploy/mqtt/growcentral-secure.conf.example` und `growcentral.acl.example`.

Für den TLS-Listener müssen Broker-Zertifikat/-Schlüssel, CA, Passwortdatei und ACL auf dem Pi existieren und für Mosquitto passend lesbar sein. Der Server-SAN muss dem tatsächlich verwendeten Hostnamen bzw. der IP entsprechen. Für jedes Gerät einen eigenen Mosquitto-Benutzer anlegen, dessen Name exakt der Geräte-ID entspricht. Die Sensor-ACL erlaubt ausschließlich seine eigenen announce/state/availability/proof-Topics und das Lesen seiner challenge. Keine fremden Topics oder `set`-Befehle. Der Backend-Benutzer `growcentral` kann lesen und Challenges senden.

Sensor-Konfiguration erfolgt im Produktionsablauf **verbindlich lokal per USB**, bevor der Sensor als einsatzbereit gilt:

```text
NET WIFI <ssid>|<password>
NET CA <base64-DER-des-öffentlichen-Broker-CA-Zertifikats>
NET MQTT <broker-host>|8883|<device-id>|<individual-password>
INFO
```

CA und individuelle Zugangsdaten sind echte Inbetriebnahmevoraussetzungen. Geheimnisse nicht in Chat, Git, Screenshots oder Diagnosepakete übernehmen. Die Firmware verwendet geprüfte TLS-Zertifikate; `setInsecure` wird nicht verwendet. Sie benötigt außerdem eine brauchbare Zeit (SNTP) für die Zertifikatsprüfung. Ohne Netzwerk/Zeitsynchronisation misst sie weiterhin, verbindet sich aber nicht unsicher.

Das Backend kann lokal über Loopback 1883 lesen; für eine eigene TLS-Verbindung `GC_MQTT_TLS=true`, `GC_MQTT_PORT=8883`, `GC_MQTT_CA_FILE` sowie private Benutzer-/Passwortbindungen konfigurieren. Der produktive Dienst liest `/opt/135er-grow-central/.env` über seine systemd-EnvironmentFile. Broker-Passwörter dürfen nicht pauschal an alle Geräte verteilt werden.

Ab Firmware **0.5.0** ist zusätzlich eine sichere BLE-Provisionierung als Recovery-/Servicepfad implementiert. Ein unkonfigurierter Sensor wirbt ausschließlich den Grow-Central-Provisioning-Service aus; Grow-Central erkennt ihn automatisch, nimmt ihn aber niemals automatisch auf. Vor der Übertragung von WLAN- oder MQTT-Geheimnissen sind alle folgenden Bedingungen erforderlich:

1. Der Nutzer startet die Aufnahme ausdrücklich in der Geräteansicht.
2. Pi und Sensor erzeugen pro Sitzung neue P-256-ECDH-Schlüssel.
3. Der Sensor signiert seinen ephemeren Sitzungsschlüssel, die frische 256-Bit-Nonce und seine Geräteankündigung mit seiner dauerhaften P-256-Geräteidentität.
4. Beide Seiten leiten mit HKDF-SHA256 einen nur für diese Sitzung gültigen AES-256-GCM-Schlüssel ab.
5. Der Nutzer muss den **BOOT-Taster direkt am XIAO mindestens etwa 0,8 Sekunden drücken**. Ohne diese physische Bestätigung werden im BLE-Servicepfad keine Zugangsdaten übertragen. Der Produktions-Erstweg bleibt USB-first.
6. Erst danach überträgt GC SSID, WLAN-Kennwort, Broker-CA und einen individuellen MQTT-Account AES-GCM-geschützt.
7. Nach der BLE-Konfiguration muss derselbe Langzeitschlüssel zusätzlich über TLS-MQTT einen frischen Nonce-Proof liefern. Erst danach setzt GC den Sensor auf `TRUSTED` und speichert Name plus Raumzuordnung.

Ein aktiver BLE-Man-in-the-Middle kann dadurch höchstens die Sitzung stören: Das Austauschen eines ephemeren Schlüssels führt zu unterschiedlichen Sitzungsschlüsseln und damit zu einem GCM-Fehler; Zugangsdaten werden nicht im Klartext gesendet. Abgelehnte/widerrufene Geräte erhalten auch über BLE keine Zugangsdaten. Bleibt die Netzwerkinbetriebnahme nach erfolgreicher BLE-Übertragung fehlerhaft, bleibt BLE als Recovery-Pfad aktiv; erst nach bestätigter TLS-MQTT-Verbindung wird die BLE-Provisionierung abgeschaltet. USB bleibt als lokaler Recovery-/Flash-Weg erhalten.

## Autonomie und Messwerte

ADC-Erfassung läuft in einer eigenen FreeRTOS-Aufgabe; blockierende Netzwerkverbindungen dürfen diese nicht stoppen. MQTT bleibt in der Netzwerk-/Hauptaufgabe; Identitätsanfragen werden gepuffert und außerhalb des MQTT-Callbacks verarbeitet. Das folgt der ausdrücklichen Deadlock-Warnung der verwendeten **256dpi/MQTT 2.5.3**-Bibliothek. WLAN und MQTT haben getrennten Backoff bis 60 Sekunden. Kalibrierung bleibt lokal; Kommunikationsverlust löst keine Aktoraktion aus.

Nonce-Antworten liefern den aktuellen Mess-Snapshot, einschließlich freigegebener RAW-/Qualitätsdiagnosewerte. Feuchte muss endlich und zwischen 0 und 100 liegen oder bei Sensorfehler `null` sein; falsche Typen und ungültige Bereiche werden verworfen. AIR_DRY/WATER_SATURATED bleibt eine technische Referenzskala, **keine bestätigte volumetrische Wassergehaltsmessung**. FRESH_SUBSTRATE_CC ergänzt die produktive Kalibrierung für frisches, gesättigtes und frei abgetropftes Substrat. Offline-Historiennachlieferung, Watchdog-/Brownout-Diagnose und echte Driftvalidierung sind weitere, hier nicht behauptete Funktionen.

## Nachweise und Grenzen

- Python-Tests einschließlich TLS-MQTT-Integration mit echtem Mosquitto 2.0.21 und Software-Sensor; anonyme Anmeldung und Schreiben unter fremder ID werden blockiert.
- Tests für unverifizierte Sensoren, manipulierte Signaturen, Topic/Typ-Bindung, Replay, Key-Wechsel, physische Fingerabdruck-Bestätigung, Fehler beim Speichern des Raums, Widerruf und Identity-Reset.
- Browserprüfung: Raum explizit anlegen, Sensorname/Fingerabdruck/Annahme, Mobile-Widerruf/Freigabe/Ablehnung, Zugriff nach Widerruf 403 und keine Ausführung manipulierter Metadaten.
- Firmware-Build für XIAO ESP32-C3: PlatformIO 6.2.0, espressif32 7.1.3, MQTT 2.5.3. Build erfolgreich; etwa 12,4 % RAM und 68,4 % Flash. CI-Build ergänzt.
- Kein Flashen eines realen Sensors, kein Pi-Image-Build oder Release, keine realen Funk-, Langzeit-, Kalibrierungs- oder Autonomie-Messungen. Der echte Pi-Broker muss noch mit seinen Zertifikaten und Accounts eingerichtet und die Firmware auf Hardware geprüft werden. Quellcode und Softwaretests allein sind keine Hardware-Freigabe.
