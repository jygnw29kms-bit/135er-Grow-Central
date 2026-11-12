# FC 3000: Mars Legacy auf dem iPhone als BLE-HCI-Referenz

Stand: 2026-11-12. Der Anwender hat bestätigt: Mars Legacy auf seinem iPhone verbindet sich erfolgreich mit der **FC 3000** und steuert die Lampe. Fokus ausschließlich FC 3000; Lüfter bleibt außerhalb des Arbeitsumfangs.

## Bevorzugte Messmethode (ohne zweiten BLE-Controller)

Die iPhone-seitige HCI-Protokollierung kann die von **der Original-App** gesendeten BLE-ATT-Schreibzugriffe erfassen. Anders als ein Raspberry-Pi-`btmon`-Mitschnitt der *fremden* iPhone↔Lampe-Sitzung sieht ein iPhone-eigenes HCI-Log den Verkehr seines eigenen Bluetooth-Controllers. Kein parallel verbundener Pi erforderlich.

**Quellen:**
- Apple PacketLogger: https://developer.apple.com/bluetooth/ (Additional Tools for Xcode, macOS)
- Apple Bluetooth Logging Profiles: https://developer.apple.com/bug-reporting/profiles-and-logs/?name=bluetooth
- Bluetooth SIG Anleitung: https://www.bluetooth.com/blog/a-new-way-to-debug-iosbluetooth-applications/
- libimobiledevice `idevicebtlogger`: https://github.com/libimobiledevice/libimobiledevice/blob/master/docs/idevicebtlogger.1

### Vorbereitung

1. iPhone und FC 3000 im bestehenden funktionierenden Zustand belassen; vorher eingestellte Lichtintensität/Zeitprogramm notieren.
2. Apple-Bluetooth-Diagnoseprofil nach den aktuellen Apple-Hinweisen auf dem iPhone installieren. Nur aus der offiziellen Apple-Quelle. Kompatibilität mit der aktuell verwendeten iOS-Version vor Ort prüfen; nicht als garantiert voraussetzen.
3. **Option A (Mac):** PacketLogger aus den Apple Additional Tools for Xcode öffnen; iPhone per USB verbinden und vertrauen; Live Capture für iPhone auswählen.
4. **Option B (Linux/Windows mit lauffähiger libimobiledevice-Installation):** Verfügbarkeit/Kompatibilität von `idevicebtlogger` und USB-Pairing zuerst prüfen. Unter Linux beispielsweise `idevice_id -l` und danach `idevicebtlogger -f pcap /privater/pfad/fc3000.pcap`. Nicht annehmen, dass alle Windows-Builds das Werkzeug enthalten.
5. iPhone-Verbindung zur FC 3000 in Mars Legacy aufbauen (während dieser Sitzung **keine** zusätzliche Bleak-GATT-Verbindung über Pi auslösen).
6. Für eine kurze, genau annotierte Aufnahme jeweils nur eine Aktion durchführen: Baseline/Idle, Ein, Aus, 25 %, 50 %, 75 %, 100 %, soweit die App diese Stufen unterstützt. Zeitstempel zur Aktion aufschreiben und den physischen Lampenzustand kontrollieren. Bestehende Programme nach dem Test wiederherstellen.
7. Aufnahme beenden und prüfen, ob ATT-Write-Pakete mit Werten und gültiger Characteristic-Zuordnung tatsächlich sichtbar sind. Falls nur HCI-Ereignisse ohne ATT-Payload sichtbar sind, keine Befehle erfinden.
8. Capture lokal privat aufbewahren. BLE-Adressen, Identifikatoren, Session- und Pairing-Informationen und Tokens nicht veröffentlichen.

### Konvertierung in vorhandene Offline-Auswertung

Ein bereits decodierter und nach Gerät/Sitzung aufgelöster ATT-Export wird nach folgenden Feldern ins private CSV-Schema gebracht:
`time_epoch,device,session,direction,characteristic_uuid,payload_hex`.
Für die Lampe muss `device=lamp` gelten. Der Zeitfenster-Export `start_epoch,end_epoch,device,session,action` erlaubt den Abgleich:

```bash
python3 scripts/mars_legacy_windows.py capture.csv windows.csv labelled.jsonl
python3 scripts/fc3000_legacy_offline_audit.py labelled.jsonl --output fc3000_candidates.json
```

Damit erhält man **nur korrelierte Kandidaten**, keine automatisch bestätigten Steuerbefehle. Vor einer Aktivierung in Grow Central müssen Modellidentität, GATT-UUID, Ausführung, Antwort und physischer Effekt in mehreren Sitzungen geprüft werden.

## Messstatus

- iPhone-Steuerung: **vom Anwender als funktionierend bestätigt**.
- HCI-Logging-Profil, USB-Logger und Live Capture: **noch nicht am Gerät geprüft**.
- FC3000-/C260-GATT-Zuordnung: **nicht bewiesen**.
- Echte FC3000-Befehlsbytes: **noch nicht aufgezeichnet**.
- Live-Grow-Central-Control: **gesperrt**.
