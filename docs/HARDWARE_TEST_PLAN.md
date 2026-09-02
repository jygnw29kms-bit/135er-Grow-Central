# Hardware Test Plan – Universal Image / Hardwareklassen

## Ziel

Reproduzierbare reale Validierung des GrowCentral-Universal-Images nach der verbindlichen Hardwarestrategie. CI-Erfolg, Image-Build und reale Hardwarevalidierung bleiben getrennte Gates.

## Release-Basis

- Aktueller Candidate: `pi-universal-alpha-0.7.5-199`
- Candidate-Commit: `34442bc41d2c79328d3d5c61eb63a744f4c433a6`
- Build 199 enthält die aktuelle headless Runtime und die Hardwareprofil-Architektur.
- Status bis zum Realtest: **CANDIDATE**.

## Zu testende Supportklassen

| Klasse | Hardware | Pflichtstatus |
|---|---|---|
| `LEGACY_LITE` | Raspberry Pi 3B / 3B+ | separater Legacy/Lite-Test |
| `FULL_SUPPORT` | Raspberry Pi 4B / 400 / CM4 | primärer Referenztest |
| `FULL_SUPPORT` Performance | Raspberry Pi 5 / CM5 | Performance-/Full-Support-Test, sofern Hardware verfügbar |

Pi 3 bleibt unterstützt, aber ein Legacy/Lite-spezifischer Fehler blockiert nicht automatisch den Full-Support-Pfad. Abweichungen müssen je Klasse dokumentiert werden.

## Verbindliche Hardwareprofil-Prüfung

Nach Boot muss die Diagnose das erkannte Modell und Profil ausweisen:

- Pi 3B/3B+ → `LEGACY_LITE`
- Pi 4/400/CM4 → `FULL_SUPPORT`, Standardprofil
- Pi 5/CM5 → `FULL_SUPPORT`, Performanceprofil
- unbekannte Hardware → `UNCLASSIFIED`

Die zentrale Quelle ist `shared/hardware_profile.py`; Komponenten dürfen keine widersprüchlichen eigenen Klassifikationen pflegen.

## Gemeinsame Baseline – alle unterstützten Klassen

1. Universal-Image frisch flashen.
2. Keine manuellen Änderungen vornehmen.
3. Setup-AP `135er-GrowCentral-Setup-XXXX` verbinden.
4. `http://10.42.0.1/` öffnen.
5. First-Boot-Assistent vollständig durchführen.
6. Heim-WLAN konfigurieren.
7. GUI- und System/SSH-Zugangsdaten getrennt setzen.
8. Setup abschließen und rebooten.
9. `http://135er-GrowCentral.local/` bzw. direkten IP-Zugriff testen.
10. GUI/Auth/Persistenz, SSH, Netzwerk, mDNS, Cloud-Link und Diagnose prüfen.

## Legacy/Lite – Pi 3B / 3B+

Zusätzlich prüfen:

- Hardwareprofil = `LEGACY_LITE`;
- Kamera bleibt im konservativen Profil (Zielmaximum 720p, reduzierte FPS);
- headless Betrieb bleibt innerhalb der konservativen Ressourcenlimits stabil;
- Worker-/Parallelitätsprofil ist konservativ;
- Diagnosehistorie ist kompakt;
- FRITZ!, Tapo, Automationen, lokale GUI und Cloud-Link bleiben grundsätzlich nutzbar;
- kein Speicherdruck/OOM im typischen Basisbetrieb.

## Full Support – Pi 4 / 400 / CM4

Zusätzlich prüfen:

- Hardwareprofil = `FULL_SUPPORT` / Standard;
- volle Nexus UI über Desktop- und Mobile-Clients;
- Full-Support-Kamera-Pfad;
- Standard-Worker und normale Diagnosehistorie;
- paralleler Betrieb von Kamera, GUI, Automationen, Diagnose und Cloud-Link;
- diese Klasse ist die Referenz für neue Features.

## Full Support Performance – Pi 5 / CM5

Zusätzlich prüfen:

- Hardwareprofil = `FULL_SUPPORT` / Performance;
- Performance-Worker aktiv;
- erweiterte Diagnosehistorie;
- volle Nexus UI über externe Clients und Kamera;
- zukünftige rechenintensive Funktionen werden bevorzugt hier validiert.

## Gemeinsame Integrationsprüfung

Nach erfolgreicher Baseline:

- FRITZ! Smart Home;
- TP-Link Tapo;
- Logitech C920/UVC;
- Bluetooth-Scan;
- Mars Hydro / iConnect Diagnose;
- Räume/Grow/Automationen;
- Support-Bundle inkl. Hardwaremodell/-profil und Schwärzung sensibler Daten;
- Cloud V7 / Entitlements.

## Testprotokoll

Für **jede** Hardwareklasse wird separat geführt:

| Bereich | Legacy/Lite Pi 3 | Full Pi 4/400 | Full Performance Pi 5 |
|---|---|---|---|
| Flash/Boot | TBD | TBD | TBD |
| Hardwareprofil korrekt | TBD | TBD | TBD |
| Setup-AP/DHCP | TBD | TBD | TBD |
| First Boot | TBD | TBD | TBD |
| WLAN/Reboot | TBD | TBD | TBD |
| mDNS/Hostname | TBD | TBD | TBD |
| GUI Auth | TBD | TBD | TBD |
| SSH Auth | TBD | TBD | TBD |
| Headless Betrieb | TBD | TBD | TBD |
| Kamera | TBD | TBD | TBD |
| Cloud V7 | TBD | TBD | TBD |
| Diagnose | TBD | TBD | TBD |

## VALIDATED-Gate

Ein Image wird nicht pauschal für alle Modelle als `VALIDATED` bezeichnet. Die Validierung wird nach Supportklasse dokumentiert. Full-Support-Freigaben für Pi 4/5 können bestehen, auch wenn ein klar abgegrenzter Pi-3-Legacy/Lite-Fix noch offen ist. Umgekehrt darf ein erfolgreicher Pi-3-Test nicht automatisch Full Support für Pi 4/5 behaupten.

Verbindliche Policy: [`HARDWARE_SUPPORT_POLICY.md`](HARDWARE_SUPPORT_POLICY.md).
