# FC 3000 / Mars Legacy: erster echter iPhone-BLE-HCI-Capture

**Datum:** 2026-11-12. **Hardware:** Mars Hydro FC 3000, Firmware V3.4. **App:** Mars Legacy (iPhone). **Capture:** per USB `idevicebtlogger` am Jens-PC. Original-PCAP bleibt ausschließlich lokal; nicht im öffentlichen Repository.

## Reale Messung

- Die zuvor funktionierende iPhone↔FC3000-Verbindung blieb der einzige aktive BLE-Controller der Lampe.
- Nutzer führte nacheinander durch: Einschalten, ungefähr 25 %, 50 %, 75 %, 100 %, Ausschalten, mit etwa 5 Sekunden Abstand.
- Aufzeichnung kontrolliert beendet: **2.221.052 Byte, 22.303 HCI-Pakete**.
- HCI H4-with-direction PCAP (DLT 201).
- **10** ATT Write Requests (`0x12`) im Capture, davon **7** dem FC3000-Kommandoformat zuordenbar; **172** Notifications. Die drei übrigen Writes dürfen nicht als Licht-Steuerbefehle interpretiert werden.
- GATT-Write-Handle der sieben Kommandos: **`0x002D`**. Die gleiche iPhone-Sitzung enthielt eine GATT-Characteristic-Discovery: **Write-Handle 0x002D → UUID `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d`** (Property Write). Notification-Handle `0x002A` → UUID `6f588463-f8f1-44f8-bdae-a1272a1b0f6e` (Property Notify). Die UUID-Zuordnung ist im iPhone-ATT-Mitschnitt nachgewiesen; Geräteidentität/Autorisierung für einen eigenen Client bleiben gesondert zu validieren.
- Bytes sind **ASCII** und bestehen aus durch `|` getrennten Feldern:

```text
<command_type>|0|<session_or_token>|<device_id>|<value>
```

Das Feld `0` und die Herkunft/Bedeutung der Sitzungskennung sind noch ungeklärt. Die echte Geräte-ID und der Token sind hier bewusst nicht veröffentlicht. **Keine Konstanten für diese Felder in einer Live-Steuerung erfinden oder dauerhaft hardcoden.**

| ISO-8601 UTC | Typ | Beobachteter Wert | Korrelation |
| --- | --- | ---: | --- |
| 18:22:14.688 | 1 | 1 | Licht Ein |
| 18:22:19.806 | 2 | 24 | Dimmen nahe 25 % |
| 18:22:22.784 | 2 | 26 | weitere kleine Reglerbewegung |
| 18:22:27.730 | 2 | 50 | 50 % |
| 18:22:32.526 | 2 | 75 | 75 % |
| 18:22:36.564 | 2 | 100 | 100 % |
| 18:22:41.257 | 1 | 0 | Licht Aus |

Die Zeitstempel liegen im Capture als UTC vor. Auf dem Windows-PC erscheinen sie möglicherweise als Lokalzeit eine Stunde später.

**Beweisstatus:** Diese sieben Folgen wurden im Original-App-HCI-Log als ATT Write Request beobachtet und korrelieren mit den vom Nutzer ausgeführten echten Aktionen. Die Übertragung über den iPhone-Controller ist **nachgewiesen**. Der exakte vollständige Befehl zum eigenständigen Ausführen durch Grow Central, inklusive Session/Autorisierung und Characteristic-UUID sowie Status-/ACK-Verhalten, ist **noch nicht vollständig validiert**.

## Bereits implementiert und am echten Capture getestet

- `scripts/fc3000_legacy_pcap_decode.py`: Offline-PCAP-Reader, nur Linktype 201, ATT Write Request/Command auf Handle 0x002D, strikte FC-ID- und Datenfeld-Validierung, **alle Identifikatoren in JSON-Ausgabe geschwärzt**.
- `tests/test_fc3000_legacy_pcap_decode.py`: sechs Tests, auf Jens-PC mit Python 3.15 erfolgreich ausgeführt (**6/6 OK**).
- Gegen Originalaufnahme auf Jens-PC ausgeführt: **7/7** relevante Aktionen dekodiert; redigierte Ergebnisse lokal unter `JL1976/Grow-Central/FC3000-BLE/fc3000_redacted_analysis.json`.
- Keine direkten BLE-Schreibzugriffe auf die Lampe vorgenommen; bestehende Control-Test-Sperre bleibt erhalten.

## Nächster technischer Schritt

1. Charakteristik-UUID zum in der iPhone-Sitzung beobachteten ATT-Handle 0x002D über GATT-Discovery derselben Lampe feststellen. Handles können je Firmware/Sitzung variieren und gehören **nicht** als dauerhaft gültige Adressen in einen Treiber.
2. Die Antwort-Notifications um die sieben Nachrichten analysieren, um ACK/Status von unabhängiger Telemetrie zu unterscheiden.
3. Die Herkunft/Neuerzeugung der Sitzungskennung und Feldsemantik durch mehrere unabhängige App-Sitzungen ermitteln. Keine Tokens in Git veröffentlichen.
4. Erst danach eine separat abgesicherte, opt-in Live-Teststeuerung für diese Lampe implementieren, mit sicherem Rücksetzen und Prüfung des tatsächlichen Lichtzustands. Die BLE-Verbindung mit Mars Legacy bleibt exklusiv.

## Datenschutz und Grenzen

Die gesamte PCAP enthält möglicherweise Gerätekennungen und nicht nur FC3000-Verkehr. Originaldatei und vollständige Payloads verbleiben in der privaten JL1976-Projektablage auf Jens-PC. Das öffentliche Repository enthält ausschließlich redigierte Befunde, Decoder-Code und synthetische Tests.

## Zweite reale Messreihe (erneute iPhone-Bedienung, 2026-11-12)

Der Nutzer meldete einen zweiten Durchlauf mit ungefähr drei Sekunden Pause. Die laufende HCI-Aufzeichnung wurde aus dem USB-Logger auf Jens-PC als separate lokale Momentaufnahme gesichert und mit `scripts/fc3000_legacy_pcap_decode.py` erneut analysiert. **Die neue Aufnahme ist eine Fortsetzung derselben PCAP, keine unabhängige neue Pairing-Sitzung.** Der Logger war während dieser Prüfung noch aktiv; nur die Momentaufnahme wurde ausgewertet.

| Zeitstempel aus PCAP (UTC) | Typ | Wert | Zuordnung |
|---|---|---:|---|
| 18:27:22.837 | 1 | 1 | Ein |
| 18:27:28.671 | 2 | 76 | Dimmen |
| 18:27:35.796 | 2 | 50 | Dimmen |
| 18:27:43.392 | 2 | 25 | Dimmen |
| 18:27:47.288 | 1 | 0 | Aus |

Die Nutzdaten folgen erneut dem Format `<type>|0|<session_or_token>|<device_id>|<value>`; das bestätigt die Bedeutung der Typen `1` (Ein/Aus) und `2` (Helligkeitswert) als **starke beobachtete Korrelation** in zwei Bedienfolgen. 76 statt 75 ist als tatsächlich übertragener Reglerwert zu behandeln, nicht zu 75 umzudichten. Die Abstände im Capture sind etwa 5,8 s / 7,1 s / 7,6 s / 3,9 s; user-genannte drei Sekunden sind keine präzisen Paketzeitstempel.

**Weiterhin offen:** Verhalten des gerätespezifischen Session-/Authentifizierungsfelds, Status-/ACK-Parsing, Reconnect, Live-Write von Grow Central; keine willkürlichen Writes und keine öffentliche Veröffentlichung des Rohcaptures.
