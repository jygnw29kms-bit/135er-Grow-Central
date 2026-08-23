# Nächstes Universal-Image: Räume, Growtagebuch und Cloud-Test

Basis ist der bestätigte Build-85-AP-/First-Boot-Pfad. Die AP-Konfiguration bleibt unverändert bei `802-11-wireless-security.pmf 1`; Cloud-Ausfall darf den lokalen Betrieb nicht beeinflussen und Remote-Befehle bleiben deaktiviert.

## Fernwartung nur für Testimages

Das Image enthält eine bewusst deaktivierte Reverse-SSH-Schnittstelle. Der Pi baut nach Aktivierung ausschließlich eine ausgehende, per Ed25519-Host-Fingerprint geprüfte Verbindung zum eigenen VPS auf. Der zurückgeleitete Port wird auf dem VPS nur an `127.0.0.1` gebunden und ist daher nicht öffentlich erreichbar. Es werden keine privaten Schlüssel im Image ausgeliefert; jeder Pi erzeugt seinen Schlüssel lokal.

Aktivierung vor dem entfernten Hardwareeinsatz:

1. `sudo grow-central-remote-maintenance init` erzeugt den Pi-Schlüssel.
2. Auf dem VPS `sudo scripts/setup-growcentral-maintenance-bastion.sh init` ausführen und den öffentlichen Pi-Schlüssel als Datei hochladen.
3. Auf dem VPS `sudo scripts/setup-growcentral-maintenance-bastion.sh add PORT PUBLIC_KEY_FILE` ausführen. Jeder Pi erhält einen eigenen Port.
4. VPS-Ed25519-Fingerprint unabhängig prüfen.
5. `sudo grow-central-remote-maintenance configure HOST growcentral-tunnel PORT SHA256:FINGERPRINT` ausführen.
6. `sudo grow-central-remote-maintenance enable` aktiviert den persistenten Tunnel.
7. Auf dem VPS erfolgt der Einstieg mit `ssh -p PORT GrowCentral@127.0.0.1`.
8. Mit `sudo grow-central-remote-maintenance disable` lässt sich die Schnittstelle jederzeit abschalten.

Die eigentliche Anmeldung am Pi erfolgt weiterhin über SSH mit dem während First-Boot gesetzten Testgeräte-Konto. Die Schnittstelle aktiviert keine Cloud-Gerätebefehle und öffnet keinen eingehenden Internet-Port am Pi.

## Automatische Build-Prüfung

- lokaler API-Healthcheck vor dem Verpacken;
- öffentlicher DNS-A-Record `135ercloud.dezender.de -> 87.106.119.187`;
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
12. Fernwartung aktivieren, über den nur auf dem VPS lokal gebundenen Tunnel anmelden, Status lesen und anschließend die Deaktivierung testen.

Abnahmekriterium: keine Regression des Build-85-Pfads, persistente Raum-/Pflanzendaten und erfolgreicher read-only Cloud-Test vor und nach dem Reboot.
