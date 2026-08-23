# Installation – GrowCentral Nexus Mobile 0.2.1

**Plattformstand:** `alpha-0.7.5` · Master `e339602` · Pi-Testkandidat **Build 118**.

## Android

1. Im neuesten erfolgreichen GitHub-Actions-Lauf das Artefakt `GrowCentral-Nexus-Android-APK` laden.
2. `135er-GrowCentral-Nexus-Android-debug.apk` auf das Gerät übertragen.
3. Installation aus der verwendeten Quelle erlauben und APK installieren.
4. Im Heimnetz `http://135er-Grow-Central.local/` verwenden.
5. Beim Pi-First-Boot kann direkt `http://10.42.0.1/` verwendet werden.
6. Die mitgelieferte `.sha256`-Datei kann zur Integritätsprüfung genutzt werden.

## iPhone / iOS – Sideloading

Der CI-Workflow erzeugt bewusst ein **unsigned Sideload-Ausgangspaket**.

1. Im neuesten erfolgreichen GitHub-Actions-Lauf `GrowCentral-Nexus-iOS-Sideload-IPA` laden.
2. `135er-GrowCentral-Nexus-iOS-Sideload-unsigned.ipa` verwenden.
3. IPA mit einem geeigneten Apple-ID-/Provisioning-basierten Sideload-Werkzeug auf PC oder Mac für das Zielgerät signieren.
4. Auf dem iPhone installieren.
5. Falls iOS eine Entwickler-/App-Vertrauensfreigabe verlangt, das verwendete Signaturprofil in den iOS-Einstellungen bestätigen.
6. App starten und lokal `http://135er-Grow-Central.local/` bzw. beim First Boot `http://10.42.0.1/` verwenden.
7. Externe Ziele werden nur als HTTPS-Adresse akzeptiert.

### Warum unsigned?

GitHub Actions enthält absichtlich keine private Apple-ID, kein persönliches Signing-Zertifikat und kein fest eingebettetes Provisioning Profile. Der letzte Signierschritt erfolgt beim Sideloading für das konkrete Gerät.

## Lokales Netzwerk auf iOS

Der iOS-Build enthält eine verständliche `NSLocalNetworkUsageDescription`, da Grow Central lokale Raspberry-Pi-Instanzen anspricht. Die App selbst enthält keine FRITZ!-, Tapo- oder sonstigen Smart-Home-Zugangsdaten.

## Sicherheitsregeln

- keine Geräte-Credentials im Mobile-Paket;
- keine Zugangsdaten in Ziel-URLs;
- lokales HTTP nur für `.local` und private IPv4-Netze;
- Remote nur via HTTPS;
- serverseitige Grow-Central-Authentifizierung bleibt maßgeblich;
- Mobile ist Bedienoberfläche, nicht Geräteautorität.

## Freigabestatus

Nexus Mobile 0.2.1 wird neu aus dem konsolidierten Repo-Stand gebaut. Android APK und iOS IPA bleiben Test-/Sideload-Builds, bis reale Gerätetests abgeschlossen sind.
