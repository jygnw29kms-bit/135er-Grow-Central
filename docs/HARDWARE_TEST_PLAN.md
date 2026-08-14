# Hardware Test Plan – alpha-0.7.5

## Ziel

Reproduzierbare Prüfung des aktuellen Raspberry-Pi-3B-Images auf realer Zielhardware. Ein Software-/CI-Test wird getrennt von einer echten Hardwarevalidierung dokumentiert.

## Zielhardware

- Raspberry Pi 3B / 3B+
- **Mars Hydro FC3000, Modelljahr 2024, USB + iConnect**
- **Mars Hydro iFresh / DF100 mit iConnect**
- DF100M / `MZ_MZF002` nur BLE-Diagnose/Reverse Engineering/Fallback
- **Logitech C920 direkt per USB am Raspberry Pi**
- FRITZ!Box mit FRITZ!SmartHome-Steckdose
- TP-Link Tapo-Geräte / Tapo-Account
- optional Shelly / Home Assistant
- kein ESP32 in der Zielarchitektur

## Bereits beobachtet

Am bisherigen Image wurden die ersten Boot-/Grundfunktionen als gut gemeldet. Bluetooth reagiert, sucht Geräte, findet Geräte und kommuniziert mit Bluetooth-Geräten. Diese Punkte bleiben im neuen `alpha-0.7.5` erneut zu prüfen, gelten aber als positiver Ausgangsstand.

## A – Neuer First Boot

1. Image frisch flashen; keine Dateien manuell ändern.
2. Setup-AP `135er-GrowCentral-Setup-XXXX` verbinden.
3. `http://10.42.0.1:8080` öffnen.
4. Mit temporärem Benutzer `GrowCentral` und Factory-Passwort an der normalen GUI anmelden und System öffnen.
5. **Systempasswort zwingend ändern.**
6. Bei aktivem Ethernet muss LAN automatisch erkannt werden.
7. Ohne LAN WLAN wählen; während des aktiven Pi-3B-APs muss die SSID manuell eingebbar sein.
8. Optional FRITZ!Box aktivieren und den dafür angelegten FRITZ!-Benutzer eingeben.
9. **Separaten GUI-Benutzer und GUI-Passwort zwingend anlegen.**
10. Setup abschließen.
11. Prüfen, dass die normale GUI danach nur mit dem neu angelegten GUI-Login erreichbar ist.
12. Reboot durchführen und Login erneut prüfen.
13. Unter System `Grow-Central-Support-latest.tar.gz` erzeugen, herunterladen und auf vollständige Schwärzung prüfen.

### Akzeptanz

- Setup-AP + DHCP funktionieren ohne manuelle Reparatur.
- Setup-Clients erhalten keinen normalen ungeschützten GUI-Zugriff auf Port 8080.
- LAN wird erkannt oder WLAN-Auswahl funktioniert.
- Factory-Systempasswort wird nicht in den Normalbetrieb übernommen.
- GUI-Login ist nach Abschluss Pflicht.
- `/api/health` bleibt lokal für Healthchecks verfügbar; normale GUI/API verlangt Authentifizierung.
- GUI-Passwort liegt nicht im Klartext in `.env`.

## B – Netzwerkbereich der GUI

Nach GUI-Login:

1. **Netzwerk** öffnen.
2. Schnittstellen-/Verbindungsstatus prüfen.
3. `WLAN SCANNEN` ausführen.
4. Prüfen, dass sichtbar `SCAN LÄUFT`, Trefferzahl, `0 Netze`, Timeout oder Fehler erscheint.
5. Test-WLAN auswählen bzw. SSID manuell eingeben.
6. WLAN beitreten.
7. Prüfen, dass das Passwort nicht in Diagnoseausgaben oder Prozessargumenten erscheint.
8. Verbindung nach Reboot erneut prüfen.

## C – FRITZ!Box / FRITZ!SmartHome

Voraussetzung: eigener FRITZ!Box-Benutzer für Grow Central mit nur den benötigten Smart-Home-Rechten.

1. GUI starten.
2. Prüfen, ob die vorhandene FRITZ!Box eindeutig erkannt wird.
3. Erwartung: Grow Central öffnet den FRITZ!-Login-Dialog.
4. Zugangsdaten eingeben.
5. Smart-Home-Geräteliste importieren.
6. FRITZ!-Steckdose in **Geräte/Strom** prüfen.
7. Gegen das FRITZ!Box-Portal vergleichen:
   - Gerätename / AIN
   - erreichbar / offline
   - Ein / Aus
   - aktuelle Leistung W
   - Gesamtenergie Wh/kWh
8. Steckdose über Grow Central ein- und ausschalten.
9. Physisches Ergebnis und anschließend zurückgelesenen Zustand prüfen.
10. Falsches FRITZ!-Passwort testen: verständlicher Auth-Fehler, kein Import.
11. FRITZ!Box kurz trennen: Gerät muss offline/Fehler anzeigen statt falscher Werte.

## D – Tapo

1. Tapo-Gerät und Pi im selben LAN betreiben.
2. Tapo-Account für Discovery/Auth verwenden.
3. Gerät lokal finden und authentifizieren.
4. Name, Modell, Zustand und – falls vom Modell unterstützt – Leistungs-/Energiewerte vergleichen.
5. Ein/Aus testen und realen Zustand zurücklesen.
6. Internet trennen: lokalen Pfad erneut testen.
7. WAN-Zugriff separat prüfen, sobald ein eigener Grow-Central-WAN-Transport implementiert ist. Die bestehende WAN-Fähigkeit der Tapo-App darf nicht fälschlich als bereits implementierter Grow-Central-Cloudpfad dokumentiert werden.

## E – Logitech C920 direkt am Pi

Die C920 ist für diesen Test physisch direkt mit dem Raspberry Pi verbunden.

### GUI-Test

1. **Kamera** öffnen.
2. `NEU ERKENNEN` ausführen.
3. Erwartung: mindestens ein `/dev/video*`-Gerät erscheint und die Logitech C920 wird nach Möglichkeit namentlich markiert.
4. Status `READ OK` und `CAPTURE` prüfen.
5. `SNAPSHOT` ausführen – ein echtes Bild muss in der GUI erscheinen.
6. Das Bedienfeld muss die **tatsächlich von der C920 gemeldeten V4L2-Controls** auflisten.
7. Verfügbare, risikoarme Regler nacheinander testen, beispielsweise Helligkeit/Kontrast/Sättigung oder Fokus, soweit sie gemeldet werden.
8. Nach jeder Änderung Snapshot aktualisieren und sichtbaren Effekt/aktuellen Wert prüfen.
9. Automatik-Regler wie Autofokus/Auto-Belichtung nur über ihre tatsächlich gemeldeten Menü-/Bool-Werte bedienen.
10. C920 abziehen: GUI muss Nicht-erkannt/Fehler anzeigen und darf nicht hängen.
11. Wieder einstecken und `NEU ERKENNEN` ausführen.

### CLI-Gegencheck

```bash
v4l2-ctl --list-devices
v4l2-ctl --device /dev/video0 --all
v4l2-ctl --device /dev/video0 --list-ctrls-menus
ffmpeg -hide_banner -f v4l2 -i /dev/video0 -frames:v 1 /tmp/c920-test.jpg
```

Gerätenummer kann abweichen. Die GUI verwendet deshalb intern `cam0`, `cam1`, … und löst diese IDs ausschließlich serverseitig auf.

## F – Bluetooth / Mars Hydro

Bluetooth-Baseline erneut prüfen:

- Scan startet sichtbar;
- Geräte werden mit Namen/Typ-Hinweisen angezeigt;
- Verbindung/GATT kann gelesen werden;
- generische Geräte werden nicht als Mars Hydro ausgegeben;
- MZ_MZF002/iFresh-Kandidaten werden nur als Diagnosekandidaten markiert.

FC3000 2024 und iFresh/DF100 bleiben iConnect-Zielgeräte. Unbekannte BLE/iConnect-Writes nicht aktivieren, bevor reale Telegramme beobachtet, korreliert und reproduzierbar validiert wurden.

## G – Security / Fehlerfälle

- ohne GUI-Login normale GUI/API nicht verwendbar;
- falscher GUI-Login wird abgewiesen;
- Smart-Home-Sourcecode bleibt deny-by-default;
- Appliance aktiviert Smart Home explizit hinter Auth + Device Approval + Writable Gate;
- unbekannte Kamera-Control-Namen und Werte außerhalb des Gerätebereichs werden abgewiesen;
- Integrationspasswörter werden nicht an Browser-Read-APIs zurückgegeben;
- DF100M-Raw-/Speed-Writes bleiben standardmäßig deaktiviert;
- `GC_REMOTE_COMMANDS=false` und `GC_CLOUD_ENABLED=false` bleiben Default des Images.

## Testprotokoll

| ID | Pfad | Aktion | Erwartung | Ergebnis |
|---|---|---|---|---|
| A01 | First Boot | Factory-Start | Setup-Assistent | TBD |
| A02 | WLAN | Scan + Join | Netzliste + Verbindung | TBD |
| A03 | GUI Auth | Logout/Login | Zugriff nur authentifiziert | TBD |
| F01 | FRITZ! | Erkennung/Login | Box + Geräte importiert | TBD |
| F02 | FRITZ!-Steckdose | ON/OFF + Telemetrie | physisch + Rücklesen korrekt | TBD |
| T01 | Tapo | lokale Discovery/Auth | Gerät erreichbar | TBD |
| C01 | C920 | Erkennung | C920 / capture-capable | TBD |
| C02 | C920 | Snapshot | echtes JPEG sichtbar | TBD |
| C03 | C920 | Control ändern | Wert + Bild reagieren | TBD |
| B01 | Bluetooth | Scan | Geräte sichtbar | bereits positiv / erneut prüfen |
| M01 | Mars Hydro | Diagnose | kein unvalidierter Write | TBD |

## Beta-Grenze

Beta erst nach wiederholbaren First-Boot-/Reboot-Tests sowie realer Prüfung von Netzwerk, GUI-Login, FRITZ!-Steckdose, C920 und den vorgesehenen Geräte-/Fehlerpfaden. Ein erfolgreicher Build allein reicht nicht.
