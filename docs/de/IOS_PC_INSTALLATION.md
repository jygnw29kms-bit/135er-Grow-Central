# 135er Grow Central für iOS – Installation über Windows-PC

## Ziel und aktueller Umfang

Die native iOS-Variante ist eine Alternative für direkte Bedienung und Messwertanzeige auf iPhone oder iPad. Der erste Testbuild enthält:

- native SwiftUI-Oberfläche im verbindlichen Show-/Test-Design;
- lokale FRITZ!Box-Anmeldung über die AVM-AHA-Schnittstelle;
- Import, Status, Leistung, Gesamtenergie, Kosten und Schalten geeigneter FRITZ!-Geräte;
- Kostenanzeige auch bei ausgeschalteter Steckdose;
- lokale History für Stunde, Tag, Monat und Jahr;
- CoreBluetooth-Suche mit Erkennung von `DF100M`/`MZ_MZF002`-Kandidaten;
- Zugangsdaten im iOS-Schlüsselbund;
- vollständige Live-Aktualisierung bei App-Aktivierung, Tabwechsel und manuellem Refresh.

Noch nicht als native iOS-Funktion validiert sind Tapo/KLAP-Steuerung, Mars-Hydro-Schreibtelegramme und USB-Kameras. Die App weist sichtbar darauf hin und täuscht diese Funktionen nicht vor.

## IPA unter Windows installieren

Das GitHub-Build erzeugt `135er_Grow_Central_iOS_unsigned.ipa`. Die Datei ist bewusst noch nicht mit einer fremden Apple-ID signiert. Die Signatur wird erst auf dem eigenen PC erstellt.

1. Sideloadly ausschließlich von `https://sideloadly.io/` laden und unter Windows installieren.
2. iPhone oder iPad per USB verbinden, entsperren und **Diesem Computer vertrauen** bestätigen.
3. Falls Windows das Gerät nicht erkennt, die aktuellen Apple-Gerätetreiber bzw. Apple Devices installieren.
4. `135er_Grow_Central_iOS_unsigned.ipa` in Sideloadly ziehen.
5. Die eigene Apple-ID eingeben und **Start** wählen. Ein App-spezifisches Passwort kann bei Konten mit entsprechender Apple-Sicherheitskonfiguration erforderlich sein.
6. Auf dem iPhone/iPad gegebenenfalls unter **Einstellungen → Datenschutz & Sicherheit → Entwicklermodus** den Entwicklermodus aktivieren und neu starten.
7. Unter **Einstellungen → Allgemein → VPN & Geräteverwaltung** dem eigenen Entwicklerprofil vertrauen, falls iOS danach fragt.
8. Die App starten und lokalen Netzwerk- sowie Bluetooth-Zugriff erlauben.

Bei einer kostenlosen Apple-ID läuft das persönliche Provisioning-Profil nach sieben Tagen ab. Danach wird dasselbe IPA erneut mit derselben Apple-ID installiert; die lokale App-Datenbank bleibt bei einem normalen Update erhalten. Eine bezahlte Apple-Developer-Mitgliedschaft oder später TestFlight/App Store vermeidet diesen wöchentlichen Testzyklus.

## FRITZ!Box einrichten

1. In der FRITZ!Box einen eigenen Benutzer für Grow Central mit Smart-Home-Rechten anlegen.
2. iPhone/iPad mit demselben Heimnetz verbinden.
3. In der App **System** öffnen.
4. Adresse `fritz.box`, Benutzer und Passwort eintragen.
5. **Anmeldung prüfen und Geräte importieren** wählen.

Das Passwort wird im iOS-Schlüsselbund nur auf diesem Gerät gespeichert. Für lokales HTTP muss iOS beim ersten Zugriff die Berechtigung für das lokale Netzwerk erhalten.

## Wichtige iOS-Betriebsgrenze

iOS hält eine normale App nicht als frei laufenden 24/7-Dienst aktiv. BLE-Ereignisse können mit dem vorgesehenen Hintergrundmodus zugestellt werden, aber beliebige Zeitpläne, sekündliche Netzwerkabfragen und Schutzautomationen sind nach Suspendierung nicht garantiert. Deshalb gilt:

- iOS-App: direkte Steuerung, Anzeige, Diagnose und History während der Nutzung;
- Raspberry Pi: weiterhin freigegebene autoritative Instanz für unbeaufsichtigte 24/7-Automation, Kamera und dauerhafte Überwachung.

## Für Entwickler

Auf einem Mac mit Xcode und XcodeGen:

```bash
cd ios
xcodegen generate
open GrowCentralIOS.xcodeproj
```

Die CI führt Unit-Tests im Simulator aus und erzeugt anschließend einen unsignierten `iphoneos`-Build für das PC-Sideloading.

