# Build 85 Folgeänderung: Kamera, HDMI und Bootdarstellung

Basis: bestätigter Build-85-Stand mit funktionierendem Boot und Setup-AP.

## Kamera
- Vorhandene dynamische UVC/V4L2-Regler bleiben die einzige Kamera-Control-Schicht.
- Grow Central begrenzt auswählbare und direkt anforderbare MJPEG-Auflösungen auf maximal 1280×720 (720p).
- Höhere C920-Modi wie 1920×1080 werden nicht angeboten und serverseitig abgewiesen.
- Eine Status-LED-Steuerung wird nur dann freigeschaltet, wenn die Kamera/der Kernel tatsächlich einen passenden UVC/V4L2-Control meldet. Es wird keine nicht vorhandene LED-Funktion vorgetäuscht.

## 7-Zoll-HDMI / Elecrow
- Der First-Boot erkennt verbundene HDMI-DRM-Connectoren und deren EDID/Modi.
- Elecrow wird über EDID-Namen erkannt; zusätzlich werden typische 7-Zoll-Modi 1024×600 und 800×480 als kompatibles Profil erkannt.
- Nur bei passendem angeschlossenem Panel wird ein KMS-Mode für den nächsten Boot gesetzt.
- Ohne passendes Display bleibt HDMI vollständig auf EDID/KMS-Automatik; Headless-Betrieb bleibt unverändert.

## Bootdarstellung
- Das vorhandene 135er-Grow-Central-Plymouth-Markenzeichen bleibt aktiv.
- `quiet` wird entfernt, `systemd.show_status=true` und `loglevel=4` werden gesetzt, damit der Boot nicht als undurchsichtiger Splash-only-Start erscheint.
- Die vorhandene Grow-Central-Konsolenbanner-Datei wird zusätzlich auf tty1 ausgegeben, zusammen mit Modell- und Displaystatus.
- Kein Autologin wird aktiviert.

## AP-Schutz
Die Displayroutine läuft ausdrücklich best-effort (`... || log ...`). Ein Fehler bei HDMI/EDID/config.txt darf den mit Build 85 bestätigten Setup-AP nicht abbrechen oder verändern. Die PMF-Einstellung des AP-Profils bleibt unverändert erhalten.
