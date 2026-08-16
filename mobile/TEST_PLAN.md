# Mobile v0.1 Testplan

## Gemeinsame Pflichtprüfungen

- Startscreen und gespeicherte Zieladresse
- Verbindung über `135er-Grow-Central.local`
- First-Boot-Verbindung über `10.42.0.1`
- GUI-Login und serverseitige Session
- Menüwechsel und vollständiger Refresh bei Pi-Ausfall
- Offline-Erkennung, Rückkehr nach Reconnect
- FRITZ!/Tapo-Geräteansichten nur über Pi-API
- Energie-/Kostenansichten und History
- Kameraansicht C920
- keine Credentials im App-Paket oder in URLs
- Remote-Ziel nur per HTTPS

## Android

- APK Installation
- WLAN-Wechsel
- App Kill/Neustart
- Hintergrund/Vordergrund

## iOS

- IPA signieren und sideloaden
- Local-Network-Berechtigung/Erreichbarkeit
- App Kill/Neustart
- Hintergrund/Vordergrund

## Freigabe

Erst wenn beide Plattformen die Pflichtprüfungen bestehen, darf Mobile v0.1 öffentlich als downloadbar markiert werden.
