# Räume & Growtagebuch – Umsetzungsstand

Stand: 2026-08-23

Umgesetzt in `master`:
- Räume anlegen und verwalten
- Geräte Räumen zuordnen
- Raum-Sensorhistorie lokal speichern
- Temperatur / Luftfeuchte / VPD / Leistung / Energie übernehmen, soweit Geräte diese Werte liefern
- Raumtagebuch
- Pflanzen pro Raum
- Pflanzentagebuch
- neue GUI-Navigation `RÄUME & GROW`
- lokale persistente Speicherung unter `/var/lib/135er-grow-central/rooms.json`
- Schreibzugriffe über bestehende authentifizierte GUI-Session bzw. API-Token

Abgrenzung:
- Build-85 Setup-AP- und First-Boot-Netzwerklogik wurde für diese Funktion nicht verändert.
- Ein neuer Image-Build wurde durch `image-builder/firstboot/BUILD_TRIGGER_20260823_ROOMS_GROWJOURNAL.txt` ausgelöst.
- Eine konkrete neue Buildnummer gilt erst nach bestätigtem GitHub-Actions-Lauf.
