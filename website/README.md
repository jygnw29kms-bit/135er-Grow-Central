# 135er-Grow Central – Product Website

Die statische Projektseite unter `website/` ist die öffentliche Produkt- und Marketingseite von **135er-Grow Central**.

**Öffentliche URL:** `https://dezender.de/GC/`  
**Version:** `alpha-0.7.5`  
**Letzter veröffentlichter Pi-Candidate:** Build 176 / `pi-universal-alpha-0.7.5-176`  
**Aktueller master:** enthält Post-176-Hardwareprofil-Runtime; nächster Universal-Image-Build erforderlich

Kanonische Quellen: [`../RELEASE_STATE.md`](../RELEASE_STATE.md) und [`../docs/HARDWARE_SUPPORT_POLICY.md`](../docs/HARDWARE_SUPPORT_POLICY.md).

## Produktbotschaft

GrowCentral bleibt eine **Local-First Universal-Raspberry-Pi-Plattform**. Die Website muss die Hardwareklassen überall konsistent kommunizieren:

- Pi 3B/3B+ = **Legacy/Lite**, weiterhin unterstützt;
- Pi 4/400/CM4 = **Full Support Standard**, empfohlen;
- Pi 5/CM5 = **Full Support Performance**, optimal für rechenintensive Funktionen;
- ein **Universal-Image** bleibt Standard;
- separate Images nur bei technisch zwingend unterschiedlichen Systembasen.

Pi 3 darf die Entwicklung neuer Full-Support-Funktionen nicht auf sein Leistungsniveau begrenzen.

## Inhalte

Die Seite erklärt:

- Universal-Image und Runtime-Hardwareerkennung;
- Hardwareprofile und Produktempfehlungen;
- First Boot / Captive Portal / Netzwerk / mDNS;
- Geräte-, Raum- und Grow-Verwaltung;
- Automationen;
- FRITZ! Smart Home und Tapo;
- Logitech C920/UVC mit hardwareabhängigen Capture-Limits;
- Kiosk/Touch und GrowCentral Nexus UI;
- Diagnose inkl. erkanntem Modell/Profil;
- Cloud V7, Entitlements und Local-First-Architektur;
- aktuellen Release-/Candidate-Status.

## Release-Kommunikation

Build 176 ist der **letzte veröffentlichte Candidate**. Die Website darf ihn nicht als aktuellen `master` oder `VALIDATED` darstellen. Seit Einführung der Hardwareprofil-Runtime ist ein neuer Universal-Image-Build erforderlich; erst nach erfolgreicher Veröffentlichung wird dessen Buildnummer als neuer Candidate übernommen.

## Deployment

Plesk-Ziel:

```text
/var/www/vhosts/dezender.de/httpdocs/GC/
```

Der Workflow `.github/workflows/deploy-website-sftp.yml` veröffentlicht `website/**` automatisch nach `https://dezender.de/GC/`.

## Design und Sicherheit

Die Website folgt dem **GrowCentral Nexus UI**, bleibt read-only und enthält keine lokalen Geräte-Credentials, Pi-Passwörter, LAN-Steuerendpunkte oder Smart-Home-Tokens.

## Lokale Vorschau

```bash
cd website
python3 -m http.server 8000
```
