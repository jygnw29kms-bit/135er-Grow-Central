# Nächstes Universal-Image: Räume, Growtagebuch und Cloud-Test

Basis ist der bestätigte Build-85-AP-/First-Boot-Pfad. Die AP-Konfiguration bleibt unverändert bei `802-11-wireless-security.pmf 1`. Nach abgeschlossener Ersteinrichtung funktioniert der lokale Betrieb auch bei einem Cloud-Ausfall weiter; allgemeine Cloud-Gerätebefehle bleiben deaktiviert.

## Fernwartung ab First-Boot, nur für Testimages

Das Image aktiviert die Reverse-SSH-Schnittstelle automatisch während der geschützten Ersteinrichtung. Der Pi baut ausschließlich eine ausgehende, per Ed25519-Host-Fingerprint geprüfte Verbindung zum eigenen VPS auf. Der zurückgeleitete Port wird auf dem VPS nur an `127.0.0.1` gebunden und ist daher nicht öffentlich erreichbar. Es werden keine privaten Schlüssel im Image ausgeliefert; jeder Pi erzeugt seinen Schlüssel lokal.

Aktivierung vor dem entfernten Hardwareeinsatz:

1. Der Cloud-/APT-Installer 6.1 richtet den Tunnel-Benutzer und den Enrollment-Dienst auf dem VPS ein.
2. Auf dem VPS `sudo growcentral-maintenance-code create` ausführen. Der ausgegebene Code ist 24 Stunden gültig und nur einmal verwendbar.
3. Den Code beim First-Boot in der Grow-Central-Oberfläche eingeben.
4. Der Pi erzeugt selbst einen Ed25519-Schlüssel, registriert nur dessen öffentlichen Anteil und prüft den VPS-Host-Fingerprint.
5. Der VPS verbraucht den Code und erlaubt diesem Schlüssel genau einen nur lokal gebundenen Tunnel-Port.
6. Der Pi startet den persistenten Tunnel automatisch; erst danach wird First-Boot als abgeschlossen markiert.
7. Auf dem VPS erfolgt der Einstieg mit `ssh -p PORT GrowCentral@127.0.0.1`. Den zugewiesenen Port zeigt die Code-Erstellung an.
8. Mit `sudo grow-central-remote-maintenance disable` lässt sich die Schnittstelle auf dem Pi jederzeit abschalten.

Die eigentliche Anmeldung am Pi erfolgt weiterhin über SSH mit dem während First-Boot gesetzten Testgeräte-Konto. Die Schnittstelle aktiviert keine Cloud-Gerätebefehle und öffnet keinen eingehenden Internet-Port am Pi.

## Automatische Build-Prüfung

- lokaler API-Healthcheck vor dem Verpacken;
- öffentlicher DNS-A-Record `135ercloud.grow-central.de -> 87.106.119.187`;
- gültiges HTTPS/TLS zum offiziellen Cloud-Endpunkt;
- erfolgreicher öffentlicher `/health`-Endpunkt;
- gültige `/.well-known/growcentral-cloud`-Discovery mit HTTPS- und WSS-Endpunkten;
- Cloud-Test ist read-only und verwendet keine Tokens oder Gerätebefehle;
- Boot- und Reboot-Smoke-Test der lokalen Anwendung bleiben verpflichtend.

## Hardware-Abnahme

1. Boot und Setup-AP wie Build 85 prüfen.
2. First-Boot über LAN oder WLAN abschließen.
3. Anmeldung über `135er-GrowCentral.local` prüfen.
4. Raum anlegen und FRITZ!/Tapo-Gerät zuweisen.
5. Sensordaten und VPD-Historie prüfen.
6. Raumtagebuch ergänzen.
7. Pflanze und Pflanzentagebuch anlegen.
8. `/usr/local/sbin/grow-central-cloud-smoke-test` ausführen; Gesamtstatus muss `OK` sein.
9. Internet kurz trennen: lokale GUI, Räume und Geräte müssen weiter funktionieren.
10. Neu starten und Persistenz von Räumen, Zuordnungen, Historie und Tagebüchern kontrollieren.
11. Cloud-Smoke-Test nach wiederhergestelltem Internet erneut ausführen.
12. Die beim First-Boot automatisch gestartete Fernwartung über den nur auf dem VPS lokal gebundenen Tunnel prüfen, Status lesen und anschließend die Deaktivierung testen.

Abnahmekriterium: keine Regression des Build-85-Pfads, persistente Raum-/Pflanzendaten und erfolgreicher read-only Cloud-Test vor und nach dem Reboot.
