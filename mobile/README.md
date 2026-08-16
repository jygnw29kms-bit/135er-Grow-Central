# 135er-Grow Central Mobile v0.1

Mobile v0.1 ist ein schlanker Capacitor-WebGUI-Client für iOS und Android. Er ersetzt den Raspberry Pi nicht und enthält keine Smart-Home-Zugangsdaten.

## Architektur

- Raspberry Pi: autoritative lokale Instanz für Geräte, Policy und Automation.
- Mobile: WebGUI-Client.
- Lokal: `http://135er-Grow-Central.local/` oder First-Boot `http://10.42.0.1/`.
- Remote: ausschließlich über eine abgesicherte HTTPS-Serveradresse.

## Lokal bauen

```bash
cd mobile
npm install
npx cap add android
npx cap add ios
npx cap sync
```

Android kann danach in Android Studio geöffnet werden:

```bash
npx cap open android
```

iOS wird auf einem Mac in Xcode geöffnet:

```bash
npx cap open ios
```

## CI-Artefakte

Der Workflow `.github/workflows/mobile-build.yml` erzeugt:

- Android Debug APK für Gerätetests;
- iOS unsigned IPA als Sideload-Ausgangspaket.

Die unsigned IPA ist nicht App-Store-signiert. Für die Installation auf einem realen iPhone muss sie mit einer zum Gerät passenden Apple-ID/Provisionierung signiert werden. Die App gilt erst nach realem iPhone- und Android-Test als veröffentlicht.

## Sicherheitsregeln

- keine FRITZ!Box-, Tapo- oder Geräte-Credentials im Mobile-Paket;
- keine Credentials in der Ziel-URL;
- Remote-Verbindungen nur über HTTPS;
- lokale HTTP-Verbindungen nur für `.local` bzw. private IPv4-Netze;
- die serverseitige Grow-Central-Sitzung bleibt maßgeblich.
