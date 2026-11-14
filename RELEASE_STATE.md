# 135er-Grow Central · Canonical Release State

## Verifizierter Pi-Livestand und Git-Synchronisierung · 14. November 2026

**Der Entwicklungsstopp ist aufgehoben.** Der installierte Raspberry Pi 4 meldet `SOURCE_COMMIT=be24ba9097c2e98eb1e3f302b5992c004d2e6e29` und `BUILD=operator-be24ba9097c2-base508` (`OPERATOR_PROVISIONED`). Dieser Betreiber-Livestand ist die Referenz für die synchronisierte Laufzeit, nicht der ältere veröffentlichte Image-Candidate 461.

Der vollständige Dateipfadvergleich ergab 755 identische Pi-/Git-Dateien, 102 absichtlich erhaltene Git-Projektdateien sowie 20 bewusst verschiedene Dokumentations-, Test- und Sicherheitspfade. Die Pi-Laufzeitmodule und die Final-Master-Weboberfläche wurden mit Original-Git-Blobhashes bestätigt; die abweichenden modernen Wartungs-/First-Boot-Sicherheitsprüfungen in Git bleiben erhalten. **QA:** 507 Tests bestanden, 2 native Broker-Tests unter dem Dienstbenutzer separat mit 13 Tests bestanden (plus 26 Untertests). Betriebsdaten und Herstellerbilder ohne Weiterverteilungsrechte gehören nicht in das öffentliche Repository.

[**Vollständiger Pi-/Git-Abgleichbericht**](docs/de/PI_GIT_RECONCILIATION_2026-11-14.md) · [Quell-Sicherungsarchiv](https://github.com/jygnw29kms-bit/135er-Grow-Central/tree/archive/pi-live-2026-11-14)

## Historischer Betreiber-Testplan vom 13. November 2026

- **Ziel:** nächstes privates Universal-Image aus dem jeweils aktuellen GitHub-`master`, kein Rückgriff auf den historischen Build 461
- **Image-Typ:** `OPERATOR_ONLY` mit individuell provisioniertem `gc-maint`-Public-Key und MeshCentral-Geräte-Enrollment
- **Fernwartung:** SSH-Start, Erstboot-Schlüsselprovisionierung, MeshCentral-Systemdienst und Watchdog integriert
- **Protokolle:** aktuelle FC3000-/MZF002-BLE-Erkennung, ausschließlich bestätigte Lese-/Statuspfade; kein unvalidiertes Schreiben
- **Weitere Bestandteile:** aktuelle USB-Sensorprovisionierung, Kalibrierung, HomeKit, Final-Master-PWA und Diagnose
- **Versionsnachweis:** `/opt/135er-grow-central/SOURCE_COMMIT`, `BUILD`, `IMAGE_DISTRIBUTION` im Image
- **Sicherheit:** Betreiber-Build ersetzt statische Test-API-Token durch individuelle Zufallswerte, keine Passwörter oder Roh-Captures aus Chats im Image
- **Abnahme:** [verbindliche Testcheckliste](docs/de/OPERATOR_IMAGE_TEST_2026-11-13.md)
- **Stand:** Quellstand, Build-Gates und Dokumentation vorbereitet; **Betreiberinstallation Base508 inzwischen bestätigt; keine neue vollständige Image-Hardwareabnahme bestätigt**.

## Verbindlicher Veröffentlichungsstopp für Pi-Images (ab 2026-11-12)

**BIS ZUR FERTIGSTELLUNG: NUR BETREIBER-IMAGES.** Es dürfen keine neuen Pi-Images in öffentlichen GitHub Releases, öffentlichen GitHub Actions-Artefakten oder auf öffentlichen Websites erscheinen. Der Quellcode bleibt Open Source. Die bisherigen Build-/Release-Kennungen sind historische Angaben und **keine aktuelle Downloadempfehlung**.

Die Image-Build-Pipeline ist manuell und ohne öffentliche Veröffentlichungs-/Artefakt-Schritte konfiguriert. Der Betreiber erstellt personalisierte Images ausschließlich auf einem autorisierten privaten Builder und behandelt das installierte MeshCentral-Enrollment sowie die resultierende Image-Datei als vertraulich.

**Altbestand:** Vor Inkrafttreten dieser Regel veröffentlichte Release-Assets sind nicht automatisch verschwunden. Sie müssen gesondert als öffentliche Downloads zurückgezogen werden. Bis eine Prüfung ihre Entfernung belegt, ist der komplette Rückzug älterer Images **OFFEN**.

## Letzter veröffentlichter Image-Candidate: Build 461

| Merkmal | Wert |
|---|---|
| Image | `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-461.img.xz` |
| Gr??e | 1.169.921.272 Byte |
| SHA-256 | `8ad6e9e9f14e275d10502df898d694dd4faa96d4426fe92aa07932b568860b16` |
| Quellstand | `5af7a97ee632a4ccaf32893c3c02735ac75bfadd` |
| Basis | Raspberry Pi OS Lite 64-bit, Universal-Image |
| Sensor-Firmware | `0.5.3` |
| Veröffentlichung | 12. November 2026 |
| Hardwarestatus | `CANDIDATE`; dieses vollständige Image noch nicht real validiert |

[Release und Downloads](https://github.com/jygnw29kms-bit/135er-Grow-Central/releases/tag/pi-universal-alpha-0.7.5-461). Firmware-Build, Userspace-Boot/Reboot, Pristine-Prüfung, Komprimierung und Veröffentlichung bestanden. Die veröffentlichte Image-Prüfsumme stimmt mit dem GitHub-Asset-Digest überein. Begleitpakete wurden auf SHA256, ZIP-Integrität, Quellstand und Firmwaremanifest geprüft.

Build 461 enthält den aktuellen USB-Sensorpfad, individuelle MQTT-TLS-Zugänge, Zertifikatskompatibilität, vollständige CA-Übertragung, Sensor-Firmware 0.5.3, HomeKit-Integration sowie die aktuellen Diagnose- und Bodenfeuchtefunktionen.

Der reale Pi-4-Sensortest vom 14. Oktober bleibt als historischer Hardwarebefund dokumentiert. Seine Erkenntnisse sind in den aktuellen Quellstand eingeflossen; separate Build-369-Hotfix-Installer geh?ren nicht mehr zum aktiven Produktpfad. [Hardwarebefund](docs/de/SENSOR_HARDWARE_TEST_2026-10-14.md), [Kalibrierung](docs/de/SOIL_SENSOR_GUIDE.md).

Der `master`-Branch kann neuere Quellcodeänderungen als Build 461 enthalten. Ein neuer Image-Candidate wird erst durch den vollst?ndigen Image-Workflow erzeugt und erh?lt einen eigenen reproduzierbaren Quellstand.

## Neu für die nächste Pi-4-Hardwareabnahme

- FC3000 und DF150-M jeweils als eigenständige Bluetooth-/2,4-GHz-WLAN-Hardwareprofile erfasst; reale BLE-/WLAN-Verbindungen und Schreibprotokolle **noch nicht validiert**.
- First-Boot-Dialog erklärt die 2,4-GHz-Anforderung. Bestehendes SSH ist bei Normal-Images opt-in, manuell erzeugte Wartungstest-Images haben einen separaten schlüsselgebundenen Pfad.
- Verbindlicher Ablauf: [Pi 4 vom Flash bis zur Geräteabnahme](docs/de/PI4_END_TO_END_ABNAHME_2026-11-12.md).

## Verbindliche Hardwarestrategie

Grow Central verwendet ein Universal-Image.

| Hardware | Klasse | Produktstatus |
|---|---|---|
| Raspberry Pi 3B / 3B+ | `LEGACY_LITE` | unterstützt mit konservativen Ressourcenlimits |
| Raspberry Pi 4B / 400 / CM4 | `FULL_SUPPORT` | empfohlene Standardplattform |
| Raspberry Pi 5 / CM5 | `FULL_SUPPORT` Performance | Plattform mit zusätzlicher Leistungsreserve |

- Pi 3B/3B+ bleibt unterstützt, begrenzt aber nicht die Entwicklung neuer Full-Support-Funktionen.
- Separate Images entstehen nur, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden.
- Runtime, Diagnose und Tests verwenden die zentrale Hardwareklassifikation.

## Release-Gates

Ein Build wird erst nach erfolgreichem Durchlauf der automatisierten Prüfungen zum `CANDIDATE`. Dazu gehören Quelltests, Sicherheitsprüfungen, Image-Anpassung, Boot, Reboot, Pristine-Prüfung, Komprimierung, Prüfsumme und Veröffentlichung.

`VALIDATED` wird ausschließlich nach dokumentierten Tests auf realer Zielhardware vergeben. Die Hardwareklassen werden getrennt bewertet:

- Raspberry Pi 3B/3B+ – Legacy/Lite;
- Raspberry Pi 4/400/CM4 – Full Support;
- Raspberry Pi 5/CM5 – Full Support Performance.

## Aktueller Testfokus

1. First Boot und sichere Vergabe eigener Zugangsdaten.
2. Setup-AP, WLAN-Übernahme und Rückfallverhalten bei Fehlkonfiguration.
3. Erreichbarkeit im Heimnetz und Persistenz nach Neustart.
4. Desktop- und Mobile-Oberfläche einschließlich iOS-WebKit-Verhalten.
5. Geräte-, Kamera-, Sensor- und Automationspfade.
6. Optionale Cloud-Verbindung ohne Abhängigkeit der lokalen Kernfunktionen.
7. Ressourcen- und Stabilitätstests getrennt nach Hardwareklasse.

## Distribution und Open Source

- Grow Central wird vollständig als Open-Source-Projekt entwickelt; das öffentliche Repository ist die zentrale Quellreferenz.
- Veröffentlichbare Images, App-Pakete, Installationsskripte und technische Dokumentation dürfen über die Projektkanäle bereitgestellt werden.
- Die öffentliche Produktseite unter `https://grow-central.de/` dient als Einstiegspunkt und kann auf Repository, Dokumentation und Releases verweisen.
- Zugangsdaten, Tokens, Schlüssel, private Zertifikate, lokale Diagnosepakete mit personenbezogenen Daten und sonstige Geheimnisse dürfen niemals in Commits oder Release-Artefakten enthalten sein.
- Für Drittanbieter-Komponenten gelten zusätzlich deren jeweilige Lizenz- und Markenbedingungen.

## Projekttrennung

Projektfremde Anwendungen sind keine funktionalen Bestandteile von Grow Central und werden nicht mehr in diesem Repository oder dessen CI-Pipelines mitgef?hrt.

## Validierung des aktuellen Kandidaten

- Python-Tests, Firmware-Build, Image-Anpassung, Userspace-Boot-/Neustartprüfung, Integritätsprüfungen und Release-Veröffentlichung für Build 461 erfolgreich; reale Hardwaretests stehen weiterhin aus.
- Home-Assistant-Komponente in CI gegen HA 2025.1.4 und 2026.10.1 geprüft; reale Sprachassistentenprüfung offen.
- Historischer Pi-4-Sensortest mit Hotfixes bestätigt; vollständiger Realtest von Build 461, Neustart-/Dauerbetrieb, Kalibrierung und andere Pi-Klassen offen.
- Status bleibt `CANDIDATE`.
