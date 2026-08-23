# Validierung Räume & Growtagebuch

Prüfreihenfolge für das nächste Raspberry-Pi-Testimage:
1. Bootlogo / Bootkonsole
2. Build-85 Setup-AP erscheint und Client erhält Adresse
3. First-Boot LAN/WLAN-Auswahl funktioniert unverändert
4. Login und 135er-GrowCentral.local
5. Räume anlegen / bearbeiten
6. FRITZ!/Tapo-Gerät einem Raum zuordnen
7. Raum-Messwert erfassen und Historie prüfen
8. Raumtagebuch-Eintrag erstellen
9. Pflanze anlegen und Pflanzentagebuch ergänzen
10. Reboot: Räume, Zuordnungen, Historie und Tagebücher bleiben erhalten
11. Nicht zugeordnete Geräte bleiben unter Geräte sichtbar
12. Schreibaktionen verlangen gültige GUI-Sitzung oder API-Authentifizierung

Abnahmekriterium: keine Regression des Build-85 AP-/First-Boot-Pfads; alle Raumdaten persistent nach Reboot.
