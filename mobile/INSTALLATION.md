# Installation – GrowCentral Nexus Mobile

## Android

1. Im GitHub-Actions-Lauf das Artefakt `GrowCentral-Nexus-Android-APK` laden.
2. `135er-GrowCentral-Nexus-Android-debug.apk` auf das Android-Gerät übertragen.
3. Installation aus der verwendeten Quelle erlauben und die APK installieren.
4. Beim ersten Start im Heimnetz `http://135er-Grow-Central.local/` verwenden.
5. Während des Raspberry-Pi-First-Boots kann direkt `http://10.42.0.1/` verwendet werden.

Die beigefügte `.sha256`-Datei kann zur Integritätsprüfung des Pakets verwendet werden.

## iPhone / iOS – Sideloading

Der CI-Workflow erzeugt bewusst ein **unsigned Sideload-Ausgangspaket**. Dadurch ist kein App-Store-Release erforderlich; das Paket wird beim Sideloading mit der Apple-ID bzw. der zum Zielgerät passenden Provisionierung signiert.

1. Im GitHub-Actions-Lauf das Artefakt `GrowCentral-Nexus-iOS-Sideload-IPA` laden.
2. Darin `135er-GrowCentral-Nexus-iOS-Sideload-unsigned.ipa` verwenden.
3. Die IPA mit einem geeigneten Sideload-Werkzeug auf PC oder Mac signieren und auf das iPhone installieren, z. B. über einen Apple-ID-basierten Sideload-Workflow.
4. Falls iOS nach der Installation eine Entwickler-/App-Vertrauensfreigabe verlangt, diese in den iOS-Einstellungen für das verwendete Signaturprofil bestätigen.
5. App starten und `http://135er-Grow-Central.local/` beziehungsweise beim First Boot `http://10.42.0.1/` eintragen.
6. Für einen externen Server akzeptiert die App ausschließlich HTTPS-Adressen.

### Warum die IPA unsigned erzeugt wird

GitHub Actions besitzt absichtlich keine private Apple-ID, kein persönliches Signing-Zertifikat und kein fest eingebettetes Provisioning Profile. Dadurch landen keine persönlichen Apple-Zugangsdaten im Repository oder im öffentlichen Build. Der letzte Signierschritt erfolgt auf dem Rechner bzw. über das Sideload-Werkzeug des Anwenders.

## Lokales Netzwerk auf iOS

Der erzeugte iOS-Build enthält eine verständliche `NSLocalNetworkUsageDescription`, weil Grow Central lokale Raspberry-Pi-Instanzen anspricht. Die App enthält selbst keine FRITZ!Box-, Tapo- oder sonstigen Smart-Home-Zugangsdaten. Apple dokumentiert für Apps mit lokaler Netzwerknutzung einen entsprechenden Nutzungstext; der tatsächliche Zugriff bleibt zusätzlich von iOS und der Zielinstanz kontrolliert.

## Sicherheitsregeln

- keine Geräte-Credentials im Mobile-Paket;
- keine Zugangsdaten in Ziel-URLs;
- lokales HTTP nur für `.local` und private IPv4-Netze;
- Remote-Verbindungen nur via HTTPS;
- die serverseitige Grow-Central-Authentifizierung bleibt maßgeblich;
- Mobile ist Bedienoberfläche, nicht Geräteautorität.

## Freigabestatus

Die Pakete sind Test-/Sideload-Builds. Eine neue Mobile-Version wird erst als hardwarevalidiert markiert, nachdem sie auf realen iOS- und Android-Geräten gegen die aktuelle Grow-Central-Basis geprüft wurde.
