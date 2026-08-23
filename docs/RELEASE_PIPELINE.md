# Release-Pipeline – 135er-Grow Central

**Stand:** 2026-08-23

## Grundsatz

Die frühere Build-70/71/72-Roadmap ist abgeschlossen und für den heutigen Projektstand nicht mehr maßgeblich. Ab jetzt wird zwischen drei Zuständen sauber unterschieden:

1. **Repository-Stand** – aktueller `master` mit den neuesten integrierten Änderungen.
2. **Image-Build** – durch GitHub Actions erzeugter Raspberry-Pi-Image-Lauf.
3. **Validierte Basis** – ein Image-Stand, der zusätzlich auf realer Hardware geprüft wurde.

Eine neue Commit- oder Workflow-Nummer wird deshalb nicht automatisch als neue validierte Hardwarebasis bezeichnet.

## Aktueller Stand

- Repository-Version: **alpha-0.7.5**
- Dokumentierte validierte Raspberry-Pi-Basis: **Build 85**
- Aktueller `master`: enthält weitere Integrations-, Test-, APT-, Cloud- und Build-Pipeline-Änderungen nach der Build-85-Basis
- Aktueller Image-Build: erneut explizit aus dem aktuellen `master` ausgelöst
- Stable-Freigabe: **noch nicht erfolgt**; Projekt bleibt in Alpha-/Hardwarevalidierung

## Seit der alten 70→71→72-Roadmap integriert

- persistente Geräte-Registry über Browser- und Pi-Neustarts;
- verschlüsselte, wiederverwendbare FRITZ!Box-Zugangsdaten mit restriktiven Dateirechten;
- FRITZ!-Livewerte, Schalten, Routinen und Templates über gespeicherte Zugangsdaten;
- Stromkostenberechnung aus der erhaltenen Gesamtenergie, sodass historische Kosten auch bei ausgeschalteter Steckdose sichtbar bleiben;
- No-Cache-Liveprüfung bei Navigation und explizite Offline-Ansicht bei Pi-Ausfall;
- authentifiziertes lokales Tapo-Onboarding über aktive IPv4-Netze mit dauerhafter Geräteübernahme;
- Cloud-/Server-Installer V6;
- signiertes APT-Repository unter `https://repo.dezender.de/apt`;
- dedizierter `Signed-By`-Keyring und Bereinigung alter Grow-Central-APT-Quellen;
- Veröffentlichung der Server- und APT-Installationsskripte über den dezender.de-Website-Workflow;
- zusätzliche Release-/Integrationsprüfungen im Repository.

## Verbindliche Release-Gates

Für jeden neuen Raspberry-Pi-Stand gilt:

1. **Quellstand integrieren** – Änderungen auf `master` konsistent zusammenführen.
2. **Automatische Tests** – Python-, Security-, Integrations- und Build-Guards müssen erfolgreich sein.
3. **Image erzeugen** – das Universal-Raspberry-Pi-Image aus exakt diesem Stand bauen.
4. **Boot-/Reboot-Test** – First Boot, GUI, Netzwerk, Persistenz und Dienste auf realer Hardware prüfen.
5. **Gerätepfade prüfen** – je nach Änderung FRITZ!, Tapo, Kamera und Mars-Hydro-Pfade testen.
6. **Support-Datei prüfen** – bei Abweichungen `Grow-Central-Support-latest.tar.gz` auswerten.
7. **Validierte Basis anheben** – erst nach erfolgreicher Hardwareprüfung wird die neue Buildnummer öffentlich als validiert bezeichnet.
8. **Veröffentlichen** – Website, README, Changelog/Release-Doku und Downloadpfade auf denselben Stand bringen.

## Distribution

### Raspberry Pi

Das Image wird über `.github/workflows/build-pi3-image.yml` erzeugt. Die Buildnummer im Image stammt aus dem GitHub-Workflow-Lauf und wird im System/Support-Kontext sichtbar gemacht.

### Cloud / Server

Der aktuelle Serverpfad verwendet:

- `scripts/install-135ercloud-v6.sh`
- `scripts/setup-135ercloud-apt-repo-v1.sh`
- signiertes Repository: `https://repo.dezender.de/apt`

Der Website-Deploy kopiert die kanonischen Skripte als:

- `https://dezender.de/135ercloud-server-install.sh`
- `https://dezender.de/setup-135ercloud-apt-repo.sh`

Die APT-Einrichtung verwendet einen eigenen Keyring und entfernt vorher alte Grow-Central-Quellen, die zu widersprüchlichen `Signed-By`-Definitionen führen könnten.

### Mobile

Die Mobile-App bleibt ein Client für die bestehende Grow-Central-WebGUI und übernimmt keine Raspberry-Pi-Funktionen.

- gemeinsame Basis: Capacitor-WebGUI-Client in `mobile/`
- iOS: Client-/Sideload-Pfad
- Android: Client-/APK-Pfad
- lokal: `http://135er-Grow-Central.local/` bzw. beim First Boot `http://10.42.0.1/`
- remote: ausschließlich über einen abgesicherten HTTPS-Serverpfad
- keine hartcodierten FRITZ!-, Tapo- oder sonstigen Gerätezugangsdaten in der App

## Release-Regel

Ein Build, Image oder Mobile-Paket gilt nur dann als **validiert/veröffentlicht**, wenn der dazugehörige Quellstand reproduzierbar ist, die relevanten automatischen Prüfungen bestanden wurden, der reale Zieltest abgeschlossen ist und der genannte Download tatsächlich bereitsteht. Laufende oder lediglich ausgelöste Builds werden nicht als validierte Hardwarebasis ausgegeben.
