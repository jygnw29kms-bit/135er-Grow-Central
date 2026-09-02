# 135er-Grow Central – Projektgeschichte / Project History

Dieses Dokument beschreibt die technische Entwicklung von der ursprünglichen Geräteidee bis zur heutigen Local-First-Plattform. Der jeweils gültige Release-Status steht in [`RELEASE_STATE.md`](RELEASE_STATE.md).

## 1. Ursprung

Ausgangspunkt war die lokale Anbindung von Grow-Hardware, insbesondere Mars-Hydro-/DF100M-Pfaden, ohne dauerhafte Abhängigkeit von Hersteller-Clouds. Der Raspberry Pi wurde als lokale Geräteautorität gewählt. Unbestätigte BLE-Schreibpfade blieben von Anfang an deny-by-default.

## 2. Local-First-Plattform

Aus der Geräteintegration entstand eine allgemeine Plattform für Smart Home, Kamera, Räume/Grow, Automationen, Energie, Diagnose, Mobile Clients und optionale Cloud-Funktionen. Lokale Kernfunktionen bleiben vom externen Server entkoppelt.

## 3. Reproduzierbares Universal-Image

GitHub Actions erzeugt ein Raspberry-Pi-OS-Lite-64-bit-Image mit First Boot, Netzwerk, Security-Härtung, GrowCentral Runtime, Bluetooth, Kiosk, Diagnose und Supportpfaden. Boot-/Reboot-, Pristine-, Packaging- und Release-Prüfungen wurden über viele Build-Iterationen gehärtet.

Der Image-Pfad entwickelte sich von Pi-3-Testimages zu einem **Universal-Image** für Pi 3B/3B+, Pi 4/400, Pi 5 und kompatible Compute Modules.

## 4. First Boot und Netzwerk

Die Appliance erhielt Setup-AP, DHCP/DNS, Captive Portal, WLAN-/LAN-Übergabe, getrennte GUI- und System/SSH-Credentials, mDNS und Recovery-Pfade. Der kanonische lokale Hostname ist `135er-GrowCentral.local`.

## 5. Geräteökosystem

Integriert bzw. vorgesehen sind insbesondere:

- FRITZ! Smart Home / AVM AHA;
- TP-Link Tapo;
- Logitech C920/UVC mit Snapshot, MJPEG, V4L2 und capability-aware Controls;
- Mars Hydro / iFresh mit iConnect-Zielpfad und BLE-Diagnose;
- Bluetooth-Discovery;
- optionale Sensorik und weitere Grow-Geräte.

## 6. GrowCentral Nexus UI

Pi-GUI, Kiosk, Mobile, Website, Repo und Release-Kommunikation folgen einer gemeinsamen Nexus-Designsprache. Die Haupt-GUI bleibt dieselbe Bedienlogik auf Desktop, Touch und Mobile.

## 7. Cloud V7

Die optionale Cloud entwickelte sich zur V7-Architektur mit Plesk- und Standalone-Routing, Geräte-/Kunden-/Gruppenverwaltung, Status/Plan/Validität, Feature-Entitlements, sicherem Pi-Abruf, zentraler Diagnose und APT-Upgradepfad.

## 8. Build 159

Build 159 war ein wichtiger konsolidierter Universal-Image-Candidate mit Cloud V7. Er blieb `CANDIDATE`, weil CI-Erfolg nicht als reale Hardwarevalidierung gewertet wird.

## 9. Build 176

Build 176 integrierte weitere First-Boot-, Captive-Portal-, mDNS-, Kiosk-, Kamera- und Diagnose-Härtungen. Das Release `pi-universal-alpha-0.7.5-176` wurde erfolgreich als Prerelease veröffentlicht. Es ist der letzte veröffentlichte Candidate vor der neuen Hardware-Profilarchitektur.

## 10. Verbindliche Hardwareklassen – 29.08.2026

Mit dem Post-176-Master wurde die langfristige Hardwarestrategie festgelegt:

- **Pi 3B / 3B+ → `LEGACY_LITE`**: weiterhin unterstützt, aber mit konservativen Ressourcenlimits;
- **Pi 4 / 400 / CM4 → `FULL_SUPPORT` Standard**: empfohlene Referenzplattform;
- **Pi 5 / CM5 → `FULL_SUPPORT` Performance**: bevorzugte Plattform für rechenintensive zukünftige Funktionen;
- unbekannte Hardware → `UNCLASSIFIED` mit konservativem Fallback.

Das Universal-Image bleibt Standard. Separate Images werden nur eingeführt, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden. Pi 3 darf neue Full-Support-Funktionen nicht mehr auf sein Leistungsniveau begrenzen.

Die zentrale Runtime-Quelle ist `shared/hardware_profile.py`. Die Diagnose weist Modell und Profil aus; CI testet die Supportklassen. Die verbindliche Policy steht in [`docs/HARDWARE_SUPPORT_POLICY.md`](docs/HARDWARE_SUPPORT_POLICY.md).

## 11. Build 199 und dauerhafte Headless-Architektur

Build 199 ist der aktuelle `alpha-0.7.5` Hardwaretest-Candidate. Er enthält die Hardwareprofil-Runtime, den dauerhaft headless ausgelegten Appliance-Betrieb, die aktuelle Desktop-/Mobile-Oberfläche und die gehärtete Ersteinrichtung ohne bekannte Factory-Passwörter. Die automatisierten Image-, Boot-, Reboot-, Pristine-, Packaging- und Release-Gates sind erfolgreich. Die reale Hardwarevalidierung steht noch aus.

## 12. Geschlossene Entwicklungsphase

Seit dem 2. September 2026 werden Quellcode, neue Builds, Images, App-Pakete, Installationsskripte und interne technische Dokumente nicht mehr öffentlich verteilt. Die öffentliche Projektseite beschreibt Produktnutzen, Geräteklassen und Entwicklungsstatus, ohne interne Downloads oder Implementierungsdetails offenzulegen.

## 13. Nächster Meilenstein

Build 199 wird auf realer Raspberry-Pi-Hardware geprüft. Die Validierung wird getrennt nach Legacy/Lite und Full-Support-Klassen protokolliert; erst danach erhält die jeweils bestätigte Klasse den Status `VALIDATED`.

---

## English summary

Grow Central evolved into a local-first Raspberry Pi automation platform with one universal image. Raspberry Pi 3B/3B+ remains supported as **Legacy/Lite**, while Pi 4/400 and Pi 5 define **Full Support** for future features. Build 199 is the current `alpha-0.7.5` hardware-test candidate. Automated gates passed; physical validation is pending. Development and distribution are now closed.
