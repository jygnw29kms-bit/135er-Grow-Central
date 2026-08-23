# Project Status – 135er-Grow Central

**Stand:** 2026-08-23  
**Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Build-118 Runtime-/Image-Anker:** `e339602476f3a716ae28abd5334cb6f96447a646`  
**Pi-Hardwaretest-Kandidat:** **Build 118** (`pi-universal-alpha-0.7.5-118`)  
**Kanonische Quelle:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

## Einordnung

Build 117 wurde erfolgreich getestet, ist durch den danach zusammengeführten e339-Laufzeitstand aber überholt. Build 118 ist deshalb der nächste reale Hardwaretest-Kandidat. Bis dieser Test abgeschlossen ist, bleibt Build 118 **CANDIDATE**. Der `master`-HEAD enthält nach e339 zusätzlich Dokumentations-, Mobile-, Design-, Packaging- und Publishing-Commits, die den vorgesehenen Pi-Laufzeitkandidaten nicht verändern.

## Aktueller Funktionsstand

| Bereich | Status | Hinweise |
|---|---|---|
| Local FastAPI / GUI | implemented | lokale autoritative Steuerinstanz |
| GrowCentral Nexus UI | implemented design baseline | verbindliche Designsprache für Pi/Web/Mobile/Repo |
| First Boot / Setup AP | implemented + früher positiv getestet | mit Build 118 erneut prüfen |
| LAN/WLAN / mDNS | implemented | Realtest Build 118 erforderlich |
| Geräte-Persistenz | implemented | Registry bleibt über Neustarts erhalten |
| FRITZ! Smart Home | implemented baseline | Livehardware weiter prüfen |
| TP-Link Tapo | implemented local onboarding | lokale Gerätepfade weiter prüfen |
| Räume / Pflanzen / Growtagebuch | implemented | aktuelle Console integriert |
| Automation | implemented baseline | Regeln/Zeitpläne im Realbetrieb prüfen |
| Energie / Kosten | implemented baseline | Gesamtenergie bleibt Basis für historische Kosten |
| Logitech C920 / UVC | implemented baseline | Snapshot/MJPEG/V4L2 vorhanden |
| Kamera-LED-Erkennung | implemented + tests | firmware-/modell-/USB-ID-bewusst |
| Kamera-LED-Steuerung | guarded implementation | nur bei erkannter Fähigkeit; Realtest Build 118 |
| Elecrow 7" Touch-Kiosk | implemented baseline | systemd-Service + gehärtete Rechte |
| Mars Hydro iConnect | architecture / experimental integration | keine unbestätigten Writes |
| DF100M BLE | diagnostics / fallback | Reverse Engineering, deny-by-default für Writes |
| Support Bundle | implemented | bevorzugte Fehleranalysebasis |
| Mobile Android | Nexus 0.2.1 client | APK über Actions |
| Mobile iOS | Nexus 0.2.1 client | unsigned Sideload-IPA über Actions |
| Cloud Server | V6 | optionaler abgesicherter Remote-Pfad |
| APT | signed repository | `https://repo.dezender.de/apt` |
| dezender.de | public read-only console | Nexus UI, keine lokalen Steuerendpunkte |

## Build 118 – Pflichtprüfungen

1. frischer Boot und Reboot;
2. Setup-AP, DHCP/DNS und Übergang ins Heimnetz;
3. lokale GUI via `135er-Grow-Central.local` und Kompatibilitätspfad `:8080`;
4. Persistenz von Setup, Geräten und relevanten Einstellungen;
5. C920-Erkennung, Snapshot, Stream und V4L2-Regler;
6. Kamera-LED-Fähigkeitserkennung und nur bei echter Unterstützung ausgeführte LED-Steuerung;
7. Elecrow-7"-Kioskstart und Touch-Bedienbarkeit, sofern Display angeschlossen;
8. FRITZ!/Tapo-Livepfade, sofern Geräte verfügbar;
9. Mars-Hydro-/BLE-Diagnosepfade ohne unbestätigte Schreibtelegramme;
10. Support-Paket bei jeder unerwarteten Abweichung.

## Sicherheitsgrenze

- Schreibpfade bleiben deny-by-default.
- Mobile Clients enthalten keine Gerätezugangsdaten.
- Remote-Zugriff benötigt HTTPS/VPN/abgesicherten Reverse Proxy.
- Öffentliche Website enthält keine LAN-Steuerendpunkte oder Smart-Home-Credentials.
- LED-/V4L2-Steuerung wird nur für erkannte, erlaubte Controls exponiert.

## Nächster Meilenstein

**Build 118 auf realer Hardware testen.** Erst nach erfolgreichem Test wird `RELEASE_STATE.md` von `CANDIDATE` auf `VALIDATED` angehoben. Ein neuer Pi-Build wird vorher nur erzeugt, wenn ein tatsächlicher Laufzeitfix nötig wird.
