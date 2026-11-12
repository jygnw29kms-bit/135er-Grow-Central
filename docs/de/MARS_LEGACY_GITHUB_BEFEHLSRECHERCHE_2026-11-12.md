# Öffentliche GitHub-Recherche: Mars Legacy BLE (12.11.2026)

## Zielhardware und aktueller Beweisstand

- Mars Hydro FC 3000, bisher BLE-Advertising-Kandidat `MZ_MARS_...C260`, genaue Identität noch nicht physisch bewiesen.
- Mars Hydro Lüfter DF150-M, bisher BLE-Advertising-Kandidat `MZ_MZF002`, genaue Identität noch nicht physisch bewiesen.
- Exklusivität je BLE-Geräteverbindung laut Anwender: Während Mars Legacy steuert, kann Grow Central nicht parallel GATT-Inspect/Notify machen.
- Auf realem Pi gemessener MZF002-Transport:
  - GATT Service `83677baa-3eb8-4866-b6b6-96e5ed5cc48d`
  - Write/RX `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d`
  - Notify/TX `6f588463-f8f1-44f8-bdae-a1272a1b0f6e`
- **Kein** dekodiertes/praxiserprobtes Herstellerkommando für Dimmen, Licht Ein/Aus oder Lüfterdrehzahl.

## Recherchefunde

| Quelle | Gefunden | Übertragbarkeit |
|---|---|---|
| [Espressif arduino-esp32 #7894](https://github.com/espressif/arduino-esp32/issues/7894) | ESP32 BLE-Server-Beispiel mit Namen `MZ_MZL-FC-E-...` und **genau denselben drei GATT-UUIDs**. Notify-/Write-Rollen passen. | Hohe Evidenz für Transport-UUIDs; Beispiel enthält **keine** echten Lampen- oder Lüfter-Payloads. |
| [davosje/marshydro_esp](https://github.com/davosje/marshydro_esp) | ESPHome-Firmware für umgeflashten originalen Bluetooth-Dongle mit lokaler Lichtregelung | Alternative Steuerung **nach Hardwareeingriff**, nicht BLE-Befehlstabelle der Legacy-App. |
| [suppqt/hass_mars_hydro](https://github.com/suppqt/hass_mars_hydro) | HA-Steuerung von Mars-Hydro-Geräten über Cloud, Archiv seit 2025-12-05 | Nicht als lokale BLE-Implementierung nutzbar. |
| [iClint/MarsHydroAPIDocs](https://github.com/iClint/MarsHydroAPIDocs) | REST/MQTT-Protokoll und Befehle des **Mars Pro MH-CB43**; BLE ausdrücklich nicht abgedeckt | Nicht für FC3000/C260 oder MZF002 übertragbar ohne reale Gerätevalidierung. |
| [KillerInk/GrowFanController](https://github.com/KillerInk/GrowFanController) | ESP32-Regler mit 0–10-V-DAC für Lüfter und Licht | Steuerarchitektur als Inspiration, **keine** BLE-Kommandos. |

## Schlussfolgerung

Die UUID-Übereinstimmung mit dem öffentlichen ESP32-Projekt ist der bislang beste externe Treffer, aber ein GATT-Transport ist **kein Befehlsprotokoll**. Keine angeblichen `on/off`-, `brightness`- oder `fan-speed`-Hex-Bytes in den Treiber übernehmen, solange echte Mars-Legacy-Sitzungen nicht beobachtet und am Zielgerät reproduziert wurden.

Die Untersuchung sollte als nächstes die mars-legacy-App-Kommunikation als **entschlüsselten BLE-ATT-Mitschnitt** mit Zeitstempeln (App-Aktionen einzeln markieren) erfassen. Die vorhandene Offline-Auswertung `scripts/mars_legacy_capture_analyze.py` kann dekodierte JSONL-Einträge nach Aktion und Session vergleichen, aber keine verschlüsselten RF-Captures eigenständig entschlüsseln. Ein BLE-Funksniffer benötigt ggf. Zugriff auf den Verbindungsaufbau/Pairing-Schlüssel; auf dem Grow-Pi laufendes `btmon` sieht nicht automatisch die Funkverbindung iPhone↔Lampe.

Gültigkeitsregel: `GATT-UUID bestätigt` ≠ `Opcode bestätigt` ≠ `Wirkung am Gerät bestätigt`.
