# 135er Grow Central für iOS – WebGUI-App über Windows installieren

## Richtige Architektur

Die iOS-App ersetzt weder den Raspberry Pi noch die Grow-Central-Serverdienste. Sie ist ein nativer, auf iPhone und iPad abgestimmter Zugang zur bestehenden WebGUI.

```text
iPhone/iPad-App ── Heimnetz ──► Raspberry Pi / Grow Central Local
       │
       └──────── HTTPS ────────► optionale Grow-Central-Serverversion
                                      │
                                      └── abgesicherte Verbindung zur lokalen Zentrale
```

- **Ohne Serverversion:** voller WebGUI-Zugriff im eigenen WLAN/LAN auf den Raspberry Pi.
- **Mit optionaler Serverversion:** derselbe WebGUI-Zugang von unterwegs über HTTPS.
- **Auf Pi/Server:** FRITZ!, Tapo, Mars Hydro, Kamera, Gerätepolicy, History und Automationen.
- **In der App:** Anzeige, Navigation, Login-Sitzung, Live-Refresh und Umschaltung zwischen Heimnetz und Server.

Die App enthält absichtlich keine eigene FRITZ!- oder Tapo-Anmeldung und steuert kein Bluetooth-Gerät direkt. Dadurch bleiben Logik, Daten und Zugangsdaten an der vorgesehenen zentralen Stelle.

## Funktionen des ersten iOS-Testbuilds

- native SwiftUI-Hülle mit `WKWebView` für die produktive Grow-Central-WebGUI;
- Standardadresse `http://135er-Grow-Central.local/` für das Heimnetz;
- frei einstellbare lokale Pi-/Serveradresse;
- optionale externe Serveradresse, ausschließlich über HTTPS;
- schnelle Umschaltung **LOCAL** / **SERVER**;
- persistente Web-Sitzung und Cookies für den GUI-Login;
- vollständige Aktualisierung ohne Browsercache beim erneuten Öffnen der App und über die Refresh-Taste;
- klarer Offline-Status mit erneutem Versuch und Wechsel auf den jeweils anderen Zugang;
- iPhone- und iPad-Layout sowie Projekt-App-Icon.

## IPA unter Windows installieren

Das GitHub-Build erzeugt `135er_Grow_Central_iOS_unsigned.ipa`. Die Signatur wird erst auf dem eigenen Windows-PC mit der eigenen Apple-ID erstellt.

1. Sideloadly ausschließlich von `https://sideloadly.io/` laden und installieren.
2. iPhone oder iPad per USB verbinden, entsperren und **Diesem Computer vertrauen** bestätigen.
3. Falls Windows das Gerät nicht erkennt, Apple Devices bzw. die aktuellen Apple-Gerätetreiber installieren.
4. `135er_Grow_Central_iOS_unsigned.ipa` in Sideloadly ziehen.
5. Die eigene Apple-ID eingeben und **Start** wählen.
6. Falls verlangt, auf iPhone/iPad den Entwicklermodus aktivieren und dem eigenen Entwicklerprofil vertrauen.
7. App starten und den Zugriff auf das lokale Netzwerk erlauben.

Bei einer kostenlosen Apple-ID läuft das persönliche Provisioning-Profil nach sieben Tagen ab. Danach wird das IPA mit derselben Apple-ID erneut installiert. Eine Apple-Developer-Mitgliedschaft bzw. eine spätere TestFlight-/App-Store-Verteilung vermeidet diesen wöchentlichen Testzyklus.

## App einrichten

### Im Heimnetz

1. iPhone/iPad mit demselben WLAN wie den Raspberry Pi verbinden.
2. In der App **Heimnetz** wählen.
3. Standardadresse `http://135er-Grow-Central.local/` verwenden oder die konkrete Pi-IP eintragen.
4. Mit dem normalen Grow-Central-GUI-Benutzer anmelden.

### Zugriff von überall

1. Die optionale Grow-Central-Serverversion unter einer gültigen HTTPS-Domain bereitstellen.
2. In der App unter **Verbindungen** diese `https://`-Adresse eintragen.
3. **Server · überall** wählen.
4. Mit dem von der Serverversion bereitgestellten Benutzer anmelden.

Die iOS-App öffnet niemals unverschlüsseltes HTTP für den externen Servermodus und umgeht keine Zertifikatsprüfung.

## Für Entwickler

```bash
cd ios
xcodegen generate
open GrowCentralIOS.xcodeproj
```

GitHub Actions kompiliert App und Test-Bundle für den iOS-Simulator und erzeugt anschließend den unsignierten Gerätebuild für das PC-Sideloading.
