# 135er-Grow Central · Nexus Mobile

Nexus Mobile ist der iOS-/Android-Client der 135er-Grow-Central-Plattform. Die App übernimmt das neue GrowCentral-Nexus-Design, bleibt aber bewusst ein Client: Raspberry Pi bzw. ausdrücklich eingerichteter Server bleiben die autoritativen Instanzen für Geräte, Policy, Automation und Zugangsdaten.

## Architektur

- **Raspberry Pi:** lokale Geräteautorität, Automationen, Smart Home, Kamera, Räume, Sensorik und Audit.
- **Nexus Mobile:** Bedienoberfläche / WebGUI-Client.
- **Lokal:** `http://135er-Grow-Central.local/` oder First Boot `http://10.42.0.1/`.
- **Remote:** ausschließlich über eine abgesicherte HTTPS-Serveradresse.
- **Branding:** 135er-Grow-Central-Logo und Markenidentität bleiben verbindlich.

## CI-Pakete

`.github/workflows/mobile-build.yml` erzeugt bei Änderungen unter `mobile/**` automatisch:

- `GrowCentral-Nexus-Android-APK`
  - `135er-GrowCentral-Nexus-Android-debug.apk`
  - SHA-256-Prüfsumme
- `GrowCentral-Nexus-iOS-Sideload-IPA`
  - `135er-GrowCentral-Nexus-iOS-Sideload-unsigned.ipa`
  - SHA-256-Prüfsumme

Die iOS-IPA wird bewusst **unsigned** erzeugt. Damit kann sie anschließend per Sideload-Workflow mit der Apple-ID bzw. Provisionierung des Zielgeräts signiert und installiert werden, ohne private Apple-Zugangsdaten in GitHub Actions abzulegen.

## Lokal bauen

```bash
cd mobile
npm install
npx cap add android
npx cap add ios
npx cap sync
```

Android:

```bash
npx cap open android
```

iOS auf macOS:

```bash
npx cap open ios
```

## Nexus Mobile UI

Der lokale Startscreen bietet:

- echtes 135er-Grow-Central-Branding;
- Local-/Mobile-/Remote-Architekturstatus;
- gespeicherte Zielinstanz;
- Direktzugriff auf die First-Boot-IP;
- automatische Kennzeichnung des Plattformtyps;
- HTTPS-Zwang für nicht-lokale Ziele;
- keine Speicherung von Benutzername oder Passwort in der Ziel-URL.

Nach dem Verbinden übernimmt die eigentliche Grow-Central-WebGUI die Sitzung und Gerätebedienung. Dadurch bleibt die Mobile-App klein und kann ohne doppelte Geräteimplementierungen dieselben neuen GUI-Funktionen nutzen wie Desktop und Tablet.

## Sicherheit

- keine FRITZ!Box-, Tapo- oder Geräte-Credentials im Paket;
- keine Credentials in Ziel-URLs;
- lokale HTTP-Verbindungen nur zu `.local` bzw. privaten IPv4-Netzen;
- Remote ausschließlich HTTPS;
- serverseitige Grow-Central-Sitzung und Rechte bleiben maßgeblich;
- iOS erhält einen verständlichen Local-Network-Nutzungstext;
- Signing-Geheimnisse werden nicht im öffentlichen CI-Workflow gespeichert.

Siehe [INSTALLATION.md](INSTALLATION.md) für Android-Installation und den iOS-Sideload-Ablauf.
