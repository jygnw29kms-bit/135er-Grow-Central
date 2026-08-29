# GrowCentral Hardware Support Policy

**Status:** verbindliche Architekturvorgabe ab 2026-08-29

## Grundsatz

GrowCentral bleibt bei **einem Universal-Image**. Die Zielhardware wird zur Laufzeit erkannt und in eine Supportklasse eingeordnet. Komponenten dürfen Raspberry-Pi-Modelle nicht unabhängig voneinander mit eigenen Sonderregeln behandeln; maßgeblich ist `shared/hardware_profile.py`.

## Supportklassen

| Hardware | Klasse | Support | Rolle |
|---|---|---|---|
| Raspberry Pi 3B / 3B+ | `LEGACY_LITE` | unterstützt, mit Ressourcenprofil | Mindestplattform / Bestandsgeräte |
| Raspberry Pi 4B / 400 | `FULL_SUPPORT` | vollständig | empfohlene Standardplattform |
| Raspberry Pi 5 | `FULL_SUPPORT` | vollständig | Performance-Plattform |
| Compute Module 4 | `FULL_SUPPORT` | vollständig, hardwareabhängig | Embedded Standard |
| Compute Module 5 | `FULL_SUPPORT` | vollständig, hardwareabhängig | Embedded Performance |
| unbekannte ARM-Hardware | `UNCLASSIFIED` | konservativ / keine Supportzusage | Diagnosemodus |

## Verbindliche Regeln

1. **Pi 3B/3B+ bleibt unterstützt**, darf aber neue Funktionen nicht auf sein 1-GB-RAM-/Performance-Niveau begrenzen.
2. **Pi 4/400/5 sind die Referenz für neue Full-Support-Funktionen.** Neue Features werden primär gegen diese Klasse spezifiziert und getestet.
3. Das **Universal-Image bleibt der einzige reguläre Download**, solange nicht unterschiedliche Kernel-, Paket- oder Service-Basen technisch zwingend werden.
4. Ein zweites Image darf erst entstehen, wenn ein klar dokumentierter technischer Grund vorliegt; reine Performance-Unterschiede reichen nicht aus.
5. Runtime-Komponenten müssen Ressourcen- oder Feature-Abstufungen über das zentrale Hardwareprofil beziehen.
6. Diagnose und Support-Bundles müssen Modell und aktives Hardwareprofil ausweisen.
7. Website, README, Release Notes, Testpläne und Supporttexte müssen dieselben Supportklassen verwenden.
8. CI muss die Klassifikation für Pi 3, Pi 4/400, Pi 5 und unterstützte Compute Modules testen.
9. Ein Release gilt nicht als vollständig hardwarevalidiert, solange die jeweilige Supportklasse nicht nach dem vorgesehenen Hardware-Testplan geprüft wurde.
10. Ein Pi-3-spezifischer Fehler darf einen Full-Support-Release für Pi 4/5 nicht grundsätzlich blockieren, muss aber als Legacy/Lite-Regression transparent dokumentiert und bewertet werden.

## Runtime-Profile

### `LEGACY_LITE` – Pi 3B / 3B+

- Kamera: konservativ, Zielmaximum 720p / reduzierte FPS;
- Kiosk: reduzierte visuelle Effekte und ressourcenschonende Defaults;
- Worker/Parallelität: konservativ;
- Diagnosehistorie: kompakt;
- lokale Kernfunktionen, Automationen, FRITZ!, Tapo, Sensorik und Cloud-Link bleiben grundsätzlich vorgesehen;
- rechenintensive neue Funktionen dürfen als eingeschränkt oder nicht empfohlen markiert werden.

### `FULL_SUPPORT` Standard – Pi 4 / 400 / CM4

- volle Nexus UI;
- Kamera bis zum freigegebenen Full-Support-Profil;
- normale Parallelität und Diagnosehistorie;
- Referenzplattform für neue Installationen.

### `FULL_SUPPORT` Performance – Pi 5 / CM5

- volle Nexus UI;
- Performance-Profil für Worker und erweiterte Diagnosehistorie;
- bevorzugte Plattform für zukünftige rechenintensive Funktionen.

## Produktkommunikation

- **Minimum / Legacy:** Raspberry Pi 3B oder 3B+
- **Empfohlen:** Raspberry Pi 4 mit mindestens 2 GB RAM
- **Optimal:** Raspberry Pi 4 mit 4 GB oder Raspberry Pi 5

Der Begriff `Legacy/Lite` bedeutet nicht End-of-Life. Er kennzeichnet eine weiterhin unterstützte Hardwareklasse mit bewusst konservativen Ressourcenlimits.
