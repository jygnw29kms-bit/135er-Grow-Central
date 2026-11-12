# Mars Legacy: BLE-Mitschnitt und Befehlsvalidierung

Stand: 2026-11-12. Zielgeräte: FC 3000 und Mars-Hydro-Lüfter (DF150-M-Kandidat). **Kein Steuerprotokoll bestätigt.**

## Technische Grenze

Die Mars-Legacy-App steuert laut Nutzer die Geräte ausschließlich über Bluetooth und die jeweilige aktive Steuerverbindung ist exklusiv. `BleakClient` auf dem Grow-Pi kann **nicht** die verschlüsselte bestehende iPhone↔Gerät-Verbindung belauschen. `ble_passive_notify_audit.py` ist nur hinsichtlich des Herstellerprotokolls schreibfrei: Es baut aktiv eine eigene GATT-Verbindung auf und aktiviert Notifications. Nicht parallel zur verbundenen Legacy-App starten.

Ein `btmon`-Log auf dem Pi zeichnet HCI-Verkehr **des Pi-Adapters** auf, nicht automatisch fremde BLE-Verbindungen. Ein geeigneter RF-Sniffer (z. B. nRF52840 mit unterstützter Sniffer-Firmware und Wireshark) kann Funkpakete erfassen; verschlüsselte Nutzdaten erfordern zusätzliche Voraussetzungen wie kontrolliertes Erfassen des Pairings/der Sitzungsschlüssel. iOS gibt den BLE-Payload der fremden App nicht einfach per Grow-Pi frei.

## Versuchsplan (Geräte einzeln)

1. Lampe/Lüfter auf aktuellem Zustand belassen; bestehende Zeitprogramme und Dimmwerte dokumentieren.
2. Gerät eindeutig identifizieren durch getrenntes Ein-/Ausschalten seiner Versorgung **nur unter Beaufsichtigung** und Advertising-Vergleich; keine Zuordnung allein anhand eines Gerätenamens.
3. Sniffer vor Verbindungsaufbau starten; RF-Kanalverfolgung und ggf. Pairing-Daten nach Fähigkeit prüfen. Keine automatische Entkopplung, kein Pairing-Reset.
4. iPhone/Mars Legacy mit *genau einem* Gerät verbinden; Uhrzeit synchron halten.
5. Je **eine** Aktion: Ausgangszustand, Ein, Aus, Ein, 25 %, 50 %, 75 %, 100 %, Aus (nur soweit App und Gerät diese Werte anbieten). Zwischen Aktionen mindestens 5 Sekunden; physische Reaktion und App-Anzeige notieren.
6. Verbindung beenden; Lampe auf zuvor dokumentierten sicheren Sollzustand zurückstellen.
7. Bei Lüfter getrennte Sitzung: Ausgangszustand und angebotene Stufen einzeln erfassen. Bestehende Klimaregelung nicht durch lange Tests unterbrechen.
8. Capture ausschließlich privat speichern; vor Veröffentlichung BLE-Adressen, Geräteseriennummern und Pairing-/Sitzungsschlüssel entfernen.

### Zu jeder Aktion erfassen

| Feld | Beispiel / Bedeutung |
| --- | --- |
| timestamp_iso8601 | lokale Zeit mit Offset |
| device_label | FC3000 oder DF150M, zunächst Kandidat |
| app | Mars Legacy, Version falls bekannt |
| firmware | falls bekannt, ansonsten unbekannt |
| action | light_on, light_off, dim_25 etc. |
| prior_state | physischer Zustand zuvor |
| observed_state | physischer Zustand danach |
| sniffer_file | lokaler Dateiname, **nicht** öffentliche Rohdaten |
| frame_numbers | Wireshark-Frame-IDs |
| connection_id | nur pseudonymisiertes Kennzeichen |
| gatt_service_uuid / characteristic_uuid | falls dekodierbar |
| opcode_payload_hex | nur nach gesicherter Dekodierung |
| notification_hex | Antwort / Quittung falls vorhanden |
| confidence | observed / repeated / verified |

## Validierungsregeln

- Drei wiederholte identische Befehlsfolgen je Aktion, einschließlich Rückmeldung und physischer Wirkung.
- Ein-/Aus-Befehl von Zustandsabfrage, Ack, Keepalive und Zeitplanänderung unterscheiden.
- Mögliche Verschlüsselung/Checksummen/Sequenznummern mit mehreren Sitzungen vergleichen.
- FC3000 und Lüfter **nicht** anhand einer identischen Service-UUID als protokollgleich behandeln.
- Steuerung zunächst ausschließlich hinter Feature-Flag und mit einzelnen freigegebenen Befehlen; kein generischer Roh-Hex-Schreibendpunkt.
- Nach Abbruch oder Timeout keinen unkontrollierten Wiederholungs-Write ausführen.
- Cloud-/Mars-Pro-API nicht als Ersatz für bestätigte Legacy-BLE-Befehle einsetzen.

## Bereits vorhandene Projektwerkzeuge

- `scripts/ble_live_audit.py`: aktiver Scan und lesender GATT-Inspect.
- `scripts/ble_passive_notify_audit.py`: **aktive GATT-Verbindung** mit Notify-Subscription, keine Hersteller-Steuerwrites.
- `app/mars_hydro_ble.py`: Diagnostik-API mit gesperrtem Control-Test.
- `docs/de/MARS_HYDRO_BLE_DIAGNOSTIK_2026-11-12.md`: aktueller Hardwarebefund inklusive UUIDs und EOFError.

## Abnahme

Erst wenn reale Captures der Legacy-App und mindestens drei reproduzierbare Aktionen an der **gleichen Geräte-/Firmwarekombination** vorliegen, wird der passende Decoder implementiert. Bis dahin bleiben die Steuerwrites deaktiviert.


## Offline-Werkzeuge für echte Legacy-Sitzungen

Der Windows-/Linux-Rechner, auf dem Wireshark oder ein BLE-Sniffer läuft, exportiert **bereits entschlüsselte und korrekt zugeordnete ATT-Nutzdaten** in eine private CSV. Ein RF-PCAP mit verschlüsseltem ATT kann von den Skripten nicht automatisch entschlüsselt werden. Die Zuordnung ATT-Handle zu Characteristic-UUID muss für **jede Sitzung** stimmen.

`capture.csv` (Kopfzeile, Platzhalterbeispiel ohne reale Befehlsbytes):

```csv
time_epoch,device,session,direction,characteristic_uuid,payload_hex
1794500000.0,lamp,session01,write,f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d,0000
```

`windows.csv`:

```csv
start_epoch,end_epoch,device,session,action
1794500000.0,1794500005.0,lamp,session01,dim_50
```

Die Platzhalterbytes `0000` sind **kein** Herstellerbefehl.

```bash
python3 scripts/mars_legacy_windows.py capture.csv windows.csv labelled.jsonl
python3 scripts/mars_legacy_capture_analyze.py labelled.jsonl --output candidate_report.json
python3 -m unittest discover -s tests -p 'test_mars_legacy*.py'
```

Die Zeitfenster sind halboffen (`start <= frame < end`) und werden pro Gerät und Sitzung geprüft. Nicht zugeordnete Daten sind `idle`, nicht automatisch Steuerbefehle. Es findet **keine** Funkverbindung, kein Pairing und kein Hersteller-Write statt. Die Analyse zeigt nur Korrelationen; ein `candidate_only`-Treffer ist keine Freigabe für die Live-Steuerung.

**Datenschutz:** `capture.csv`, `windows.csv`, `labelled.jsonl` und `candidate_report.json` bleiben lokal und privat. Keine rohen Pairing-Schlüssel, Adressen oder unbekannten Nutzdaten ins öffentliche Git.
