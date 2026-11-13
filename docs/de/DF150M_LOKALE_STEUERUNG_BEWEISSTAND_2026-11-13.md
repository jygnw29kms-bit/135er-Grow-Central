# DF150-M / MZF002: Nachgewiesener lokaler Steuerweg, 13.11.2026

## Aktuelles Live-Ergebnis auf dem Grow-Pi

Das eigene Gerät `MZ_MZF002_68756_A0A3B35EFDC8` ist über BlueZ/Bleak direkt verbindbar.
Read-only GATT-Inspection war erfolgreich. Der Fan-Controller bietet:

- Service: `83677baa-3eb8-4866-b6b6-96e5ed5cc48d`
- Notify: `6f588463-f8f1-44f8-bdae-a1272a1b0f6e`, Handle 41 in der getesteten Sitzung
- Write: `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d`, Handle 44 in der getesteten Sitzung

Handles sind nicht stabil; **immer UUIDs verwenden.** 23-Felder-MZF002-Notifications sind bereits live dekodierbar, darunter Ein/Aus, Sollwert %, Ist-RPM, Temperatur, Feuchte.

## Fremde Nachweise

- https://community.home-assistant.io/t/mars-hydro/672657/30 — Nutzer mipovi9185 berichtet (Okt. 2025) über funktionierende lokale iFresh-Steuerung vom Raspberry Pi mit GATT writes und BLE-Rückmeldung.
- https://community.home-assistant.io/t/mars-hydro/672657/34 — Er stellt ausdrücklich klar: GATT-Befehle mit festen Payloads, nicht die MQTT-Nachrichten aus MarsProHA.
- https://community.home-assistant.io/t/mars-hydro/672657/60 — Am 11.11.2026 werden noch immer UUIDs und konkrete Payload-Beispiele öffentlich erfragt. Keine gesicherte, öffentliche Payload im Thread.
- https://www.mars-hydro.com/media/download/Mars-Fan-iFresh-2025-User-Manual.pdf — Bluetooth/WLAN über USB-Controller, separate RJ12/iHub-Option.

## Warum ein Kommando noch NICHT gesendet wurde

Die private iPhone-Aufzeichnung vom 12.11.2026 enthält 266 decodierte MZF002-Notifications und die Sollwertfolge 25→50→75→100→Aus. Im selben HCI-Lauf wurden **0 BLE ATT Write Requests/Commands** beobachtet. Das belegt **nicht**, dass der Lüfter keine GATT-Steuerung unterstützt; es belegt, dass die App-Aktionen in diesem Lauf nicht als iPhone-BLE-Write sichtbar waren. Mögliche Ursache ist WiFi/Cloud als Steuerkanal. Ein Aufzeichnen der iPhone-App-Bedienung ist daher kein Ersatz für ein bestätigtes Payload vom lokal arbeitenden Entwickler.

## Implementierungsentscheidung

1. DF150-M Telemetrie lokal weiter produktiv auslesen.
2. Freie lokale BLE-Schnittstelle und Geräte-Identität anhand Name und GATT-Service prüfen.
3. **Keine** FC3000-Schreibbefehle, unbekannte Bytefolgen oder pauschale 1-Byte-Dimmwerte an den Fan schicken.
4. Schreibpfad erst nach ermittelter konkreter GATT-Payload/Checksumme/Sitzungslogik aktivieren. Zunächst ausschließlich einen explizit bestätigten Einzelbefehl, kein Auto-Replay.
5. Erfolg nur nach neuem MZF002-Notify mit geprüftem Sollwert bzw. Ein/Aus-Status melden. Kein Erfolg allein aus GATT-Write-ACK ableiten.

## Alternative Pfade

Die Legacy-Cloud-Integration unter https://github.com/suppqt/hass_mars_hydro ist mit E-Mail/Passwort verifiziert, **nicht** mit „Mit Apple anmelden“. Daher kein automatischer Einsatz und keine Aufforderung zum Auslesen von Apple-Login-Tokens.

Die MH-CB43-MQTT-Befehle aus https://github.com/iClint/MarsHydroAPIDocs sind für ein anderes Gerät und dürfen nicht blind an MZF002 gesendet werden.

**Status: Lokale MZF002-BLE-Verbindung, Notification-Lesung und GATT-Write-Characteristic bestätigt; Steuer-Payload und reale Steuerung weiterhin unbestätigt.**
