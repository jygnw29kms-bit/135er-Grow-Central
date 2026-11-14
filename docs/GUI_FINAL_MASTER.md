# Grow Central · Final Master GUI

Verbindlicher UI-Master: vom Nutzer freigegebene Screenshot-Vorlage, November 2026. Eine responsive Web- und PWA-Oberfläche unter /ui, keine parallele Legacy-GUI.

## Aufbau
Linke Navigation: Dashboard, Geräte, Klima, Kamera, Growbuch, Räume, Apple Home, Cloud, System.
Dashboard: botanischer HERO mit Grow-Central-Branding, vier Live-Telemetrie-Kacheln, Mars Hydro FC3000 / DF150-M mit echter BLE-Steuerung und Herstellerbildern; rechts Core-/Cloud-/HomeKit-Status, C920-Livekamera, Verlauf aus echten Grow-Ereignissen; unten das echte Growbuch.
Mobil: identische Daten und APIs, responsive Karten und Fußnavigation.

## Datenregeln
Mockup-Zahlen wie 24,6 °C, 58 %, 1320 RPM, 40 % und Beispiel-Bewässerungen sind **keine** Live-Daten. Die Implementierung liest ausschließlich bestätigte API-Antworten. Fehlende Daten erscheinen als „—“ bzw. sauberer Leerzustand. Keine fiktive Pflanzenphase, kein Leistungs-/PPFD-Messwert ohne Sensor.

## Bildquellen (privates System)
* FC3000, Herstelleroriginal 1600×1600: https://cdn.shopify.com/s/files/1/0555/7266/0422/files/fc3000_smart.jpg?v=1684813843
* DF150-M, Herstelleroriginal 1500×1500: https://marshydroled.ca/cdn/shop/products/2_a2ddeabd-1bab-4918-911f-7d11e4b96442.jpg?v=1722485403 ; Gerät aus Originalbild als 1460×560 zugeschnitten
* HERO-Pflanzenbild, Anton Darius / Unsplash: https://unsplash.com/photos/water-droplets-on-green-leaf-CGSzrn5C2aU

Die Originalbilder liegen lokal auf dem privaten Pi und werden nicht ins öffentliche Repository übernommen. Gerätefotos werden proportional mit object-fit:contain und ohne künstliches Upscaling angezeigt; Text, Rahmen und Icons sind CSS/SVG-vaktorbasiert. Die C920 unterstützt dynamische Wahl ihrer real gemeldeten MJPEG-Modi (Standard 1280×720, sofern unterstützt).

## Verdrahtung
* Mars Hydro BLE: /api/mars-hydro/ble/fast-lamp-status und /fast-fan-status; POST /fast-*-control (physische Bestätigung, keine wiederholten Schaltbefehle).
* Kamera: /api/v1/camera/status, /stream, /controls.
* Growbuch: /api/v1/rooms/{room_id}/journal (GET/POST/PUT/DELETE), Pflanzen und Ereignisse; Bilder über /api/v1/grow-photos.
* Apple Home: /api/v1/homekit/status.
* FRITZ/Tapo: /api/v1/smarthome/overview; nur tatsächlich registrierte Geräte.
* Cloud: /api/cloud/status, Geräte-Pairing; Fernsteuerung separat abnehmen.

## Abnahme
Journal-Erstellen/Bearbeiten/Löschen mit isolierter Testdatenbank geprüft. Kein Testdatensatz im produktiven Raum hinterlassen. Backend, Cloud-Link und HomeKit beim Deployment aktiv.
