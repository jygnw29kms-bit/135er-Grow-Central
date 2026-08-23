# 135er-Grow Central – Projektgeschichte / Project History

Dieses Dokument fasst die technische Entwicklung von der ursprünglichen DF100M-Idee bis zum heutigen konsolidierten Plattformstand zusammen. Der aktuelle Release-Status selbst steht ausschließlich in [`RELEASE_STATE.md`](RELEASE_STATE.md).

## 1. Ursprung: lokaler Grow-Controller

Ausgangspunkt war der Wunsch, Mars-Hydro-Geräte nicht dauerhaft von einer Hersteller-App oder Cloud abhängig zu machen. Der Raspberry Pi wurde als lokale Masterplattform gewählt. Die frühe Arbeit konzentrierte sich auf DF100M-BLE-Discovery, GATT-Inspektion und Notification-Capture.

Schreibzugriffe blieben von Anfang an sicherheitsbewusst deny-by-default. Nicht reproduzierbar bestätigte BLE-Payloads werden bis heute nicht als validiertes Protokoll dargestellt.

## 2. Vom Fancontroller zur Local-First-Plattform

Aus dem BLE-Experiment entstand eine allgemeine Grow-/Smart-Home-Plattform:

```text
Browser / Tablet / Mobile
          |
  135er-Grow Central Local
       Raspberry Pi
   /       |       |       \
Smart    Kamera   Grow     Diagnose
Home      UVC    Räume
          |
 optional HTTPS Server
```

Der Pi bleibt lokale Geräteautorität. Cloud-/Server-Komponenten sind optional und dürfen lokale Kernfunktionen nicht blockieren.

## 3. Plattform- und Sicherheitsbaseline

Die Architektur wurde um SQLite/PostgreSQL-Zielmodelle, Rollen/RBAC, Sites, Geräte, Sensoren, Historie, Automationen, Events, Alerts, Commands, Audit und Backups erweitert. Nicht jede Architekturkomponente ist gleichzeitig vollständige Produktionsruntime; Dokumentation unterscheidet deshalb `implemented`, `experimental`, `candidate`, `validated`, `baseline/design` und `planned`.

Schreibpfade benötigen bekannte/erlaubte Geräte und Authentifizierung. Remotezugriff benötigt zusätzlich gesicherten Transport.

## 4. Reproduzierbarer Raspberry-Pi-Imagebuilder

GitHub Actions erzeugt ein flashbares Raspberry-Pi-OS-Lite-64-bit-/Debian-trixie-Image. Frühere Buildprobleme – etwa ein volles Root-Dateisystem oder UFW im chroot – führten zu einem gehärteten Builder mit verifizierter Basis, erweitertem Dateisystem, First-Boot-Firewall, systemd-Checks und Support-/Diagnosepfaden.

Die Buildnummer wird automatisch aus dem GitHub-Actions-Lauf in das Image geschrieben.

## 5. First Boot und Netzwerk

Die Appliance erhielt einen echten First-Boot-Prozess mit temporärem Setup-AP, DHCP/DNS, LAN/WLAN-Konfiguration, mDNS und verpflichtender Passwortänderung. Der lokale Standardzugriff wurde auf `135er-Grow-Central.local` vereinheitlicht; Port 8080 bleibt als Kompatibilitätspfad erhalten.

Support-Bundles, persistente Journals und Wiederherstellungs-/Health-Pfade wurden ergänzt, damit reale Hardwarefehler reproduzierbar diagnostiziert werden können.

## 6. Smart Home: FRITZ! und Tapo

Die Plattform entwickelte sich von einer Bridge-Idee zu echten lokalen Integrationspfaden:

- FRITZ! Smart Home / AVM AHA mit Geräteinformationen, Status, Leistung, Gesamtenergie, Temperatur und Schalten, soweit die Hardware es meldet;
- verschlüsselte, wiederverwendbare lokale FRITZ!-Zugangsdaten;
- authentifiziertes lokales Tapo-Onboarding über aktive IPv4-Netze;
- persistente gemeinsame Geräte-Registry;
- Energie-/Kostenlogik auf Basis erhaltener Gesamtenergie.

## 7. Kamera: Logitech C920 / UVC

Logitech C920 wurde Referenzkamera. Hinzu kamen:

- sichere `/dev/video*`-Erkennung;
- Snapshot und native MJPEG-Streams;
- dynamische V4L2-Regler;
- Fokus-/Belichtungs-/Weißabgleichsteuerung nur über bekannte Controls;
- Schutz vor beliebigen browserseitig gelieferten Device-Pfaden/Controlnamen.

Im aktuellen e339-Stand wurde zusätzlich eine **firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung** integriert. LED-Steuerung wird nur angeboten/ausgeführt, wenn das konkrete Gerät die Fähigkeit unterstützt. Passende Tests sichern diese Semantik ab.

## 8. Räume, Pflanzen und Automation

Die GUI wurde um Räume & Grow, Gerätezuordnung, Sensordaten, Growtagebuch, Pflanzen und Automation erweitert. Damit wird Grow Central zunehmend von einer Geräteoberfläche zu einer strukturierten lokalen Betriebsplattform.

## 9. Elecrow 7-Zoll Touch-Kiosk

Für den lokalen Betrieb wurde ein Elecrow-7-Zoll-Kioskpfad ergänzt:

- lokale Touch-Oberfläche;
- systemd-Kiosk-Service;
- gehärtete Dateirechte;
- direkte Verwendung derselben Grow-Central-WebGUI statt einer zweiten Bedienlogik.

## 10. GrowCentral Nexus UI

Website, Pi-GUI, Kiosk, Mobile, Repo und Release-Grafiken werden ab jetzt als eine Produktfamilie behandelt. Logo und Branding bleiben unverändert; Layout, Farben, Statussemantik, Panels, Typografie und Responsive-Regeln folgen dem verbindlichen [`GrowCentral Nexus UI`](docs/DESIGN_SYSTEM_NEXUS.md).

## 11. Mobile Apps

Android und iOS sind Capacitor-WebGUI-Clients – keine Pi-Ersatzimplementierungen.

- Android: APK-Artefakt;
- iOS: unsigned Sideload-IPA, die für das Zielgerät beim Sideloading signiert wird;
- lokale private HTTP-Ziele erlaubt;
- Remote ausschließlich HTTPS;
- keine FRITZ!-/Tapo-/Geräte-Credentials im Mobile-Paket.

Der aktuelle konsolidierte Mobile-Stand wurde auf Nexus Mobile 0.2.1 angehoben.

## 12. Cloud Server V6 und Signed APT

Der optionale Serverpfad wird über `scripts/install-135ercloud-v6.sh` bereitgestellt. Der APT-Bootstrap nutzt das signierte Repository `https://repo.dezender.de/apt`, einen dedizierten `Signed-By`-Keyring und bereinigt alte konfliktbehaftete Quellen.

Der dezender.de-Deploy veröffentlicht Website, Cloud-/APT-Installer, Release-State und SHA-256-Prüfsummen gemeinsam.

## 13. Build 117 → Build 118

Build 117 war ein erfolgreicher realer Image-Teststand. Danach wurden Kamera-LED-Logik, Tests und der aktuelle GUI-/Netzwerk-/FRITZ-/Tapo-/C920-/Elecrow-Stand zusammengeführt. Der Konsolidierungsanker ist:

```text
e339602476f3a716ae28abd5334cb6f96447a646
```

Damit ist Build 117 funktional überholt. Der nächste Hardwaretest soll mit:

```text
Build 118
pi-universal-alpha-0.7.5-118
```

erfolgen.

Build 118 ist **CANDIDATE**, nicht automatisch `VALIDATED`. Dokumentations-, Website- oder Mobile-Änderungen erzeugen bewusst keinen künstlichen Build 119; ein neuer Pi-Build wird erst bei einem tatsächlichen Laufzeitfix nötig.

## 14. Aktueller nächster Meilenstein

Build 118 real auf Zielhardware prüfen:

1. Fresh Boot / Reboot;
2. First Boot, AP, DHCP/DNS;
3. LAN/WLAN/mDNS;
4. GUI und Persistenz;
5. C920 Snapshot/MJPEG/V4L2;
6. LED-Capability Detection und guarded LED control;
7. Elecrow-Kiosk, sofern vorhanden;
8. relevante FRITZ!/Tapo/Mars-Pfade;
9. Support-Bundle bei jeder Abweichung.

Erst danach wird der Kandidat in [`RELEASE_STATE.md`](RELEASE_STATE.md) auf `VALIDATED` angehoben.

---

## English summary

135er-Grow Central evolved from DF100M BLE research into a local-first Raspberry Pi control platform covering smart home, camera, rooms/grow, automation, energy, Mobile clients, optional Cloud Server V6 and a signed APT distribution path. The current consolidated code anchor is `e339602`; Build 117 was successfully tested but is superseded. **Build 118 (`pi-universal-alpha-0.7.5-118`) is the next hardware-test candidate and remains CANDIDATE until real target-hardware validation passes.**
