# Grow Central: GUI-Bereinigung und Funktionsinventar (13.11.2026)

## Verbindliche Architektur
Eine GUI: web/gc-final.html, gc-final.css, gc-final.js über /ui. Dieselbe Oberfläche für Desktop und PWA, offizielles Branding und App-Icons. Login und First Boot sind separate Sicherheitsabläufe, keine Grow-Central-Oberflächen.

## Bestätigte Funktionen
- Mars Hydro FC3000: BLE dauerhaft, Ein/Aus, Helligkeit 10–100 %, Status; HomeKit Ein/Aus nach Feedback-Fix vom Nutzer bestätigt.
- Mars Hydro DF150-M: BLE dauerhaft, Ein/Aus, Stufe 25–100 %, tatsächliche RPM, Temperatur, Luftfeuchte; bei Aus 0 RPM und 0 % aktive Leistung, Sollwert separat.
- Logitech C920: Kamera am Pi erkannt, MJPEG-Endpunkt bereit, Overlay Datum/Uhrzeit/aktuelle Temperatur und Feuchte; Browserbild nicht visuell abgenommen.
- HomeKit: gekoppelte Bridge, drei veröffentlichte Zubehörgeräte (Licht, Abluft, Klima).
- Raum-API: ein Raum tatsächlich vorhanden.
- SQLite-Messarchiv: Lampen-/Lüfterdatensätze abrufbar.
- FRITZ! AHA und TP-Link Tapo: lokale Adapter vorhanden, derzeit null Geräte auf diesem Pi registriert. Keine fiktiven Geräte.
- PWA: Manifest und Original-Branding-Icons; iOS-Installation erfordert verlässliches HTTPS.

## Erfasst, aber nicht als fertig abgenommen
Raum erstellen/bearbeiten, Geräte einem Raum zuordnen, ESP/XIAO-Provisionierung, Sensoridentität und 3-Schritt-Bodenfeuchte-Kalibrierung, Anbauprofile und Phasen, Pflanzen-/Raumtagebuch, Bewässerung, Regeln/Zeitpläne, Energie-/Kostenanalyse, Aufnahmen/Zeitraffer, Exporte, Backup/Updates, Netzwerk-/Systemverwaltung, UI-Layout-Editor.

## Altoberflächen
Platform, Console, Index, Mobile, UI-Editor, Mars-BLE-Diagnose sowie ältere JS/CSS-Skripte waren parallel vorhanden. Ihre Quellen sind im geschützten Root-Archiv unter /var/lib/135er-grow-central/gui-source-archive/ui-legacy-before-unification-20261113.tar.gz gesichert. Geräte-, Sensor-, HomeKit- und Archivdaten bleiben unangetastet. Keine alten GUI-Routen oder statisch abrufbaren Editors in der neuen Anwendung.
