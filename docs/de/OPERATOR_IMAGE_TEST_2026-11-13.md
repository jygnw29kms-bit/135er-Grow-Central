# Betreiber-Testimage: Hardwareabnahme am 13. November 2026

**Ziel:** erster sauberer Test des nächsten privat erstellten Raspberry-Pi-Images aus dem aktuellen Grow-Central-`master`. **Status: Vorbereitung**, noch kein erzeugtes und hardware-validiertes Betreiber-Image.

## Vor dem Flashen: Freigabe-Gates

- [ ] Privates Betreiber-Image ausschließlich auf autorisiertem Builder erzeugt; nicht öffentlich hochgeladen
- [ ] Exakte `SOURCE_COMMIT` und `BUILD` dokumentiert; Quellstand enthält die aktuellen FC3000/MZF002-Telemetrie-Änderungen
- [ ] SHA-256 des privatisierten Images erzeugt und lokal geprüft
- [ ] MeshCentral-ARM64-Agent und individueller Geräte-Enrollment-Datensatz im Betreiber-Image vorhanden, keine gemeinsamen Fleet-Keys
- [ ] Persönlicher SSH-`ed25519`-Public-Key auf der Bootpartition für `gc-maint` provisioniert, kein privater Schlüssel dort
- [ ] `GC_API_TOKEN` und `GC_LOCAL_API_TOKEN` sind beim Betreiber-Build individuell generiert, nicht der bekannte Image-Testwert
- [ ] Ohne private Agent-Daten kein Betreiber-Image als „remote ready“ ausgeben

## Erstboot auf dem Pi 4

1. Frische Test-SD verwenden; bestehende SD als unmodifiziertes Rückfallmedium aufbewahren.
2. Pi booten, Sprache DE/EN prüfen, Netzwerk und erstes Admin-Konto einrichten.
3. Ausgeschaltete Lampe und ausgeschalteten Lüfter zunächst **nicht automatisch steuern**.
4. Netzwerkadresse und `http://135er-grow-central.local/` prüfen. Wenn mDNS zwei Adressen meldet, am Router die gültige Pi-Adresse anhand MAC/ARP verifizieren und Alias-Duplikate beseitigen.
5. Betriebssystemdiagnose ausführen: `sudo gc-operator-image-check`. Der Befehl gibt keine Tokens oder Passwörter aus.
6. Über einen autorisierten, **anderen** Computer mit `ssh -i /path/to/owner_key gc-maint@<Pi-IP>` anmelden; `sudo -n id` nachweisen.
7. In MeshCentral prüfen, dass der Pi als **eigenständiges Gerät** online erscheint; Desktop-PCs ausschalten dürfen den Zugriff nicht unterbrechen.
8. Den Pi regulär neu starten und wiederholen: SSH, MeshCentral, Weblogin, lokale Daten, Sensorzuordnungen, HomeKit bleiben erreichbar.

## Grow-Central-Funktionstests

| Test | Akzeptanzkriterium | Status |
|---|---|---|
| Final-Master-UI | iPhone/PWA und Desktop entsprechen dem verbindlichen Master; alle sichtbaren Menüs funktionsfähig | OFFEN |
| DE/EN-Erstboot | Sprache, Netzwerk und Login bleiben nach Neustart bestehen | OFFEN |
| FC3000 Bluetooth | eindeutig erkannte Geräteidentität und getrennte Live-Daten, keine blind gesendeten GATT-Writes | OFFEN |
| MZF002 / DF150-M | echte Live-Werte für Temperatur, Luftfeuchte, Drehzahl und Stellwert, statuskorrekte Abschaltung | OFFEN |
| Luftstrom/Druck | CFM/Pa nur anzeigen, wenn diese Werte tatsächlich per verifiziertem Protokoll gelesen werden | OFFEN |
| WLAN 2,4 GHz | FC3000 und DF150-M getrennt prüfen; BLE-Erkennung allein gilt nicht als WLAN-Kopplung | OFFEN |
| XIAO ESP32-C3 | USB-Erkennung, echte Geräteidentität, Freigabe und Raumzuordnung | OFFEN |
| Bodenfeuchtesensor | AIR_DRY → WATER_SATURATED → FRESH_SUBSTRATE_CC; gespeicherte Kalibrierung und Live-Messung | OFFEN |
| Apple HomeKit | echter QR-Code, erfolgreiche Home-Kopplung, Bodenfeuchte-Werte statt HomePod-Werte | OFFEN |
| Kamera C920 | nur bei erkannter Kamera Live-Bild anzeigen, kein Demo-Bild als Livestream | OFFEN |
| Watchdog/Agenten | automatische Dienststarts beim Boot und Wiederverbindung nach Netzwerkunterbrechung | OFFEN |
| API / Health | HTTP 200 für `/api/health`, Auth-Schutz für sensible Endpunkte, keine bekannten Factory-Tokens | OFFEN |
| SSH-Sicherheit | individueller Key, keine geteilten Passwörter/Host-Keys, keine öffentliche Router-Portfreigabe | OFFEN |

## Referenz der Mars-Hydro-Aufzeichnung vom 12. November

Der Lüfter wurde mit 25/50/75/100 Prozent durchgetestet. Nach Aufzeichnung traten u. a. ungefähr 820 RPM bei 25 %, 2100 RPM bei 50 %, 2660 RPM bei 75 % und 2980 RPM bei 100 % auf. Die Werte sind **historische Capture-Beobachtungen**, keine Live-Daten des neuen Images. Eine spätere Statusanzeige darf diese Werte nicht als aktuelle Messung ausgeben.

Lüftersteuerbefehle und Geräteidentität sind nicht abschließend verifiziert. **Write-Zugriffe bleiben gesperrt**, bis Geräteidentität und Protokoll nachgewiesen sind. Alle Roh-Captures mit Sitzungstokens bleiben außerhalb öffentlicher Git-Repositories und außerhalb verteilter Images.

## Freigaberegeln

- `CANDIDATE` nur nach erfolgreichem, dokumentiertem Build + statischen und Userspace-Gates.
- `HARDWARE_VALIDATED` erst nach **echtem** Flash-/Boot-/Reboot-/Sensor-/HomeKit-/BLE- und Fernwartungstest.
- Keine öffentlichen Images bis zur ausdrücklichen späteren Freigabe des Betreibers.
- Kritische Funktion fehlerhaft: zum vorherigen SD-Medium zurückkehren, keine ungeprüfte Datenmigration.

**Stand heute:** Source-Integrationen und Testhilfen sind vorbereitet; Image-Erstellung, Gerätregistrierung und echte Hardwarevalidierung stehen noch aus.
