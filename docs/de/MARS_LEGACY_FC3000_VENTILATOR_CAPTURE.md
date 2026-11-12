# Mars Legacy: FC 3000 und Ventilator parallel analysieren (2026-11-12)

## Aktueller Umfang

- FC 3000: Geräte-ID aus Mars Legacy bestätigt, Firmware V3.4, echte iPhone-ATT-Schreibbefehle für Licht Ein/Aus/Dimmen beobachtet. Grow-Central-Replay weiterhin nicht freigegeben.
- Ventilator: Nutzer bestätigt, dass der Ventilator in Mars Legacy aktuell gekoppelt ist, aber ausgeschaltet bleibt. Frühere BLE-Advertising-Bezeichnung `MZ_MZF002_0_A0A3B35EFDC8` laut Screenshot; die Zuordnung zu DF150-M ist noch nicht hardwareseitig gesichert.
- Für den MZF002-Kandidaten wurden am Pi Service-UUID `83677baa-3eb8-4866-b6b6-96e5ed5cc48d`, Write-UUID `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d` und Notify-UUID `6f588463-f8f1-44f8-bdae-a1272a1b0f6e` ermittelt. **Gleiche GATT-UUIDs sind kein Beweis für gleiche Befehls-Payloads.**
- Von der ersten iPhone-HCI-PCAP (3.930.276 Bytes) gehören 12 von 13 Writes an Handle 0x002D eindeutig zur FC 3000. Im untersuchten ATT-Write-Payload wurde keine Ventilator-Gerätekennung gefunden. Ein unzugeordneter Write darf nicht als Lüfterbefehl eingestuft werden.

## Neue Messreihe

Eine getrennte HCI-Aufnahme auf Jens-PC mit `idevicebtlogger` wurde unter `JL1976/Grow-Central/FC3000-BLE/mars_legacy_lamp_fan_20261112.pcap` gestartet. Das iPhone wurde per USB erkannt, der Logger bestätigte die Verbindung.

**Wichtig:** Ein HCI-Log erfasst nur die Bluetooth-Verbindungen des iPhones. »Gekoppelt« im Sinne von in der App hinterlegt garantiert **nicht**, dass gerade eine aktive BLE-Verbindung zum ausgeschalteten Ventilator besteht. Keine Verbindung zum Ventilator erzwingen und keine Aktion automatisch ausführen.

Für den nächsten praktischen Test zuerst ausschließlich das Ventilator-Gerät in Mars Legacy öffnen, ohne Ein/Aus oder Geschwindigkeit zu ändern. Sofern bereits im ausgeschalteten Zustand eine Verbindung besteht, können wir Discovery, Status/Notifications und mögliche Statusabfragen im iPhone-HCI-Log beobachten. Falls keine Daten auftreten, ist das ein Messbefund und kein Grund für erfundene Schreibbefehle. Erst mit ausdrücklicher Nutzerfreigabe eine kontrollierte Stufenfolge am Ventilator ausführen.

## Architektur

- Getrennte Geräte-ID, BLE-Verbindungszustände, Rohdaten- und Decoder-Pipelines für Lampe und Ventilator.
- Ein zentraler Connection Manager begrenzt aktive Verbindungsversuche, respektiert exklusive Mars-Legacy-BLE-Verbindung und vermeidet automatische Reconnect-Stürme.
- Keine öffentliche Veröffentlichung von Roh-HCI-PCAPs oder Tokens; keine aktive Grow-Central-Steuerung bis gerätespezifischer Validierung.
- Die belegten FC3000-Steuerbefehle niemals automatisch an den Ventilator senden.
