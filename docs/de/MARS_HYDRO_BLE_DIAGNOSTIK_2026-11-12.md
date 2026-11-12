# Mars Hydro FC3000 / DF150-M: lokale Bluetooth-Diagnose

**Stand:** 2026-11-12. **Implementiert:** lesende Diagnostik in GrowCentral. **Noch nicht nachgewiesen:** Geräteidentität und modellabhängiges Steuer-/Telemetrie-Protokoll auf der echten Hardware.

## Einstieg

Nach dem First Boot und der Admin-Anmeldung im GrowCentral-Geräte-Dashboard **„Bluetooth-Diagnose öffnen“** auswählen. Alternativ ist die Diagnose unter `http://135er-grow-central.local/static/mars-hydro-ble.html` erreichbar.

Die API liegt unter `/api/mars-hydro/ble` und nutzt dieselbe Schreibberechtigung wie die übrige geschützte Geräteverwaltung. Kein Internet und keine Mars-Hydro-Cloud erforderlich.

| Route | Funktion | Verändert Hardware? |
|---|---|---|
| `GET /status` | Fähigkeiten und Freigabestand | Nein |
| `POST /scan` | BLE-Geräte und Werbeinformationen erfassen | Nein |
| `POST /inspect` | Verbindungsaufbau, Dienste, Properties und alle lesbaren Characteristics (max. 48) | Nein; nur GATT-Reads |
| `POST /observe` | Eine verifizierbar notify-fähige Characteristic für 0,5–8 s beobachten | Nein; aktiviert Notify-Abonnement |
| `POST /control-test` | Gesperrter Platzhalter für später bestätigte Steuerbefehle | **Nein, HTTP 403** |

Scan-Ergebnisse enthalten eine **zeitlich beschränkte Kandidaten-ID** und Herstellerhinweise, aber noch keine verifizierte Identität. Die Rohdaten sind begrenzt; keine dauerhaft offenen Bluetooth-Verbindungen und kein beliebiges Raw-Write. Die Diagnose stellt keine RPM-, Temperatur-, Lüfterstufen- oder Lichtleistungswerte dar, solange deren Zuordnung nicht zweifelsfrei bestätigt ist.

## Praktischer erster Versuch am Pi 4

1. Lampe und DF150-M einzeln einschalten. Bluetooth an beiden Geräten aktiviert lassen. Falls die Hersteller-App eine exklusive Verbindung hält, ihre Verbindung kontrolliert trennen.
2. Im Browser **Bluetooth-Geräte suchen**. Den jeweiligen Kandidaten anhand des Gerätenamens und getrennten Ein-/Ausschaltens eindeutig zuordnen. Keine Annahme nur anhand eines ähnlichen Namens.
3. **Ausgewähltes Gerät auslesen**. GATT-Service-UUIDs, Characteristics, Properties und lesbare Rohwerte protokollieren.
4. Für eine notify-fähige Characteristic zunächst eine 4-Sekunden-Aufnahme im unveränderten Zustand durchführen.
5. Nun **am manuellen Regler oder in der Hersteller-App** einen bekannten Wert verändern (z. B. Lüfterstufe 25 % → 50 %), und erneut aufnehmen. Wenn die App Bluetooth exklusiv belegt, ist dieser parallele Versuch nicht möglich; dann nach der Änderung erneut verbinden und auslesen.
6. Mindestens drei reproduzierbare Zustände vergleichen, z. B. 25/50/75 %; dabei auch Gerät-Neustart und Verbindungswiederaufbau testen.
7. Aus den beobachteten Rohdaten erst nach Beleg eine modell- und firmwaregebundene Zuordnung von Characteristic, Payload, Bestätigung und physischem Effekt ableiten. Vorher **keine** Steuerbefehle an die Geräte schicken.

**Hinweis:** Subscriben auf Notifications ist eine BLE-GATT-Operation und aktiviert einen Kommunikationskanal. Sie ist kein dokumentierter Gerätesteuerbefehl und bewirkt nicht zwangsläufig, dass ein Controller Statusmeldungen sendet. Falls keine Nachrichten eingehen, muss der notwendige sichere Status-Request über echte App-Beobachtung ermittelt werden.

## Realer Pi-4-Nachweis vom 12.11.2026

Auf dem GrowCentral-Pi (Build 495) wurde der BLE-Scan mit BlueZ/Bleak und
anschließendem **schreibgeschützten GATT-Inspect** über den Wartungszugang
erfolgreich ausgeführt.

- **MZ_MZF002** war erreichbar; RSSI im geprüften Lauf etwa -65 dBm.
  Die genaue Zuordnung zum DF150-M bleibt bis zur hardwareseitigen
  Identitätsprüfung offen.
- Proprietärer GATT-Service: `83677baa-3eb8-4866-b6b6-96e5ed5cc48d`.
- Characteristic **notify**: `6f588463-f8f1-44f8-bdae-a1272a1b0f6e`.
- Characteristic **write**: `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d`.
  **Die Existenz dieser Characteristic erlaubt keine Schreibtests.**
- Standarddienste `1800` und `1801`; drei lesbare Standard-Characteristics
  `2aa6`, `2a01` und `2a00` erfolgreich gelesen.
- Keine GATT-Schreibbefehle gesendet, Identität/Protokoll **nicht** validiert.
- Im Webjournal: erster Inspect um 16:14 mit BleakDBusError/HTTP 502,
  zweiter um 16:14 mit HTTP 200. Fehlerbehandlung bei konkurrierenden
  Verbindungen beziehungsweise kurzzeitigem Verbindungsabbruch verbessern.
- Ein weiterer BLE-Scan fand 20 Geräte, davon MZF002 als Mars-Hydro-Kandidat.
  **C260 war bei diesem Lauf nicht sichtbar**, wurde bei früheren
  BlueZ-Scans aber als `MZ_MARS_0_…C260` empfangen.

**Nächste Abnahme:** Passiv die Notify-Characteristic beobachten, die
rohen Antworten reproduzierbar erfassen und die Gerätezuordnung separat
bestätigen. Ohne bestätigte Befehlsfamilie keine Steuerfunktion freigeben.

## Technische Grenzen

- Die Implementierung umfasst derzeit **Scan → GATT Read → Notify → Vergleich**, aber keine bestätigte FC3000-/DF150-M-Befehlsfamilie.
- Bereits dokumentierte DF100M-UUIDs, DF100M-Payload-Kandidaten und der Mars-Pro-Cloud-Adapter sind **keine** ausreichende Grundlage für direkte Schreibzugriffe auf FC3000 oder DF150-M.
- Falls ein Gerät nur nach einem authentifizierten Challenge-Response antwortet, kann die rein lesende Diagnose begrenzt sein. Keine zufälligen Authentifizierungs- oder Schreibversuche.
- WLAN der beiden Geräte unterstützt nur 2,4 GHz, ist für den vorgesehenen reinen BLE-Pfad jedoch nicht zwingend erforderlich.
- Die Hardwareabnahme erfordert echten Raspberry-Pi-4-Test, Erkennung beider Geräte, erfolgreich ausgelesene Informationen und dokumentierte Vergleichsmessungen.

## Zukunft: kontrollierte Steuerungsprüfung

Erst nach einem an **genau dieser** Modell-/Firmwarekombination beobachteten und reproduzierbaren Befehl kann eine separate, standardmäßig gesperrte Steuerprüfung eingeführt werden: Geräteidentität bestätigen, definierte Befehlskodierung anwenden, erlaubten Wertebereich erzwingen, explizite Bedienerfreigabe, nur ein Befehl pro Transaktion, Antwort/Status und physische Wirkung verifizieren, Audit-Eintrag. Kein generischer Hex-Write-Endpunkt.

Bestehende Rohdaten aus dem Test nicht ungeprüft öffentlich veröffentlichen; MAC-Adressen und lokale Netzwerkinformationen gehören in eine private Diagnoseablage.
