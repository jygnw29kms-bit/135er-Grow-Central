# 135er-Grow Central · Nexus Mobile 0.2.1

Nexus Mobile ist der iOS-/Android-Client der 135er-Grow-Central-Plattform. Die App folgt dem verbindlichen GrowCentral-Nexus-Design und bleibt bewusst ein Client: Raspberry Pi bzw. ausdrücklich eingerichteter Server bleiben die autoritativen Instanzen für Geräte, Policy, Automation und Zugangsdaten.

**Kanonischer Plattformstand:** `alpha-0.7.5` · Branch `master` · Build-118-Runtime-/Image-Anker `e339602` · Pi-Hardwaretest-Kandidat **Build 118** (`pi-universal-alpha-0.7.5-118`).

> `e339602` ist der Pi-Laufzeitanker des Kandidaten. Der Repository-HEAD enthält danach zusätzliche Mobile-/Doku-/Packaging-Commits, ohne den Pi-Kandidaten künstlich hochzuzählen.

## Architektur

- **Raspberry Pi:** lokale Geräteautorität, Automationen, Smart Home, Kamera, Räume, Sensorik und Audit.
- **Nexus Mobile:** Bedienoberfläche / WebGUI-Client.
- **Lokal:** `http://135er-Grow-Central.local/` oder First Boot `http://10.42.0.1/`.
- **Remote:** ausschließlich über eine abgesicherte HTTPS-Serveradresse.
- **Branding:** Logo und Markenidentität bleiben unverändert; UI folgt GrowCentral Nexus.

## CI-Pakete

`.github/workflows/mobile-build.yml` erzeugt bei Änderungen unter `mobile/**` automatisch beide Plattformpakete neu:

- `GrowCentral-Nexus-Android-APK`
  - `135er-GrowCentral-Nexus-Android-debug.apk`
  - SHA-256-Prüfsumme
- `GrowCentral-Nexus-iOS-Sideload-IPA`
  - `135er-GrowCentral-Nexus-iOS-Sideload-unsigned.ipa`
  - SHA-256-Prüfsumme

Die iOS-IPA wird bewusst **unsigned** erzeugt. Sie wird beim Sideloading mit der Apple-ID bzw. Provisionierung des Zielgeräts signiert; private Apple-Zugangsdaten liegen nicht im Repository oder CI-Workflow.

## Nexus Mobile UI

Der Startscreen bietet:

- offizielles 135er-Grow-Central-Branding;
- Local-/Mobile-/Remote-Architekturstatus;
- gespeicherte Zielinstanz;
- Direktzugriff auf die First-Boot-IP;
- Plattformkennzeichnung;
- HTTPS-Zwang für nicht-lokale Ziele;
- keine Credentials in der Ziel-URL.

Nach dem Verbinden übernimmt die lokale Grow-Central-WebGUI die Sitzung und Gerätebedienung. Damit stehen neue Pi-GUI-Funktionen wie Kamera-/LED-, Raum-, Energie- oder Geräteansichten ohne doppelte native Implementierung auch mobil bereit.

## Sicherheit

- keine FRITZ!Box-, Tapo- oder Geräte-Credentials im Paket;
- lokale HTTP-Verbindungen nur zu `.local` bzw. privaten IPv4-Netzen;
- Remote ausschließlich HTTPS;
- serverseitige Grow-Central-Sitzung und Rechte bleiben maßgeblich;
- iOS erhält einen Local-Network-Nutzungstext;
- Signing-Geheimnisse werden nicht im öffentlichen CI gespeichert.

## Release-Regel

Mobile 0.2.1 wird neu aus dem konsolidierten Repository-Stand gebaut. Die Pakete bleiben Test-/Sideload-Artefakte, bis reale iOS-/Android-Gerätetests gegen Build 118 bzw. die dann gültige Pi-Basis abgeschlossen sind.

Siehe [INSTALLATION.md](INSTALLATION.md) und [`../RELEASE_STATE.md`](../RELEASE_STATE.md).
