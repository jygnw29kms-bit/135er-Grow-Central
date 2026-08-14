<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · Local-first Raspberry Pi control" width="100%"></p>

<p align="center">
  <a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="docs/README.md">Docs</a> · <a href="docs/de/INSTALLATION.md">Installation</a> · <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.5-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Raspberry%20Pi%203B-35e8da?style=flat-square&labelColor=061015">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha%20hardware%20validation-ffb52b?style=flat-square&labelColor=061015">
  <img alt="Security" src="https://img.shields.io/badge/security-GUI%20login%20%2B%20deny--by--default-71ff3b?style=flat-square&labelColor=061015">
</p>

<p align="center"><code>LOCAL-FIRST</code> · <code>RASPBERRY PI</code> · <code>MARS HYDRO iCONNECT</code> · <code>FRITZ! SMART HOME</code> · <code>TAPO</code> · <code>LOGITECH C920</code></p>

> [!WARNING]
> **Alpha / Hardwarevalidierung.** Der aktuelle Teststand bootet und die Bluetooth-Grundfunktionen wurden auf echter Hardware positiv beobachtet. Das ersetzt noch keine vollständige Freigabe aller Netzwerk-, Smart-Home-, Kamera- und Mars-Hydro-Pfade.

## Deutsch

**135er-Grow Central** ist eine local-first Steuer- und Überwachungsplattform. Der Raspberry Pi 3B bleibt die autoritative lokale Instanz für GUI, Gerätepolicy, Smart Home, Kamera, Diagnose und optionale Cloud-Anbindung.

### alpha-0.7.5 – aktueller Zielstand

Der neue First-Boot-Ablauf findet direkt in der geschützten Haupt-GUI unter **System** statt:

1. **Systempasswort ändern – Pflicht.** Das Factory-Passwort darf nicht in den normalen Betrieb übernommen werden.
2. **Heimnetzwerk einrichten.** Aktives LAN wird automatisch erkannt. Ohne LAN zeigt das Setup eine WLAN-Liste und verlangt die Auswahl bzw. manuelle SSID.
3. **FRITZ!Box optional anbinden.** Für Grow Central soll ein eigener FRITZ!Box-Benutzer mit den für Smart Home notwendigen Rechten verwendet werden.
4. **Grow-Central-GUI absichern – Pflicht.** Ein separater GUI-Benutzer und ein mindestens 12 Zeichen langes GUI-Passwort werden eingerichtet. Danach schützt eine serverseitige Sitzung die lokale GUI und API.

Das Setup-WLAN verwendet `135er-GrowCentral-Setup-XXXX`. Die normale GUI ist ab dem ersten Start unter `http://10.42.0.1:8080` mit dem temporären Zugang `GrowCentral / grow-central-test` verfügbar. Nach Abschluss bleibt die interne Domain fest `http://135er-Grow-Central.local:8080`. Da der einzelne WLAN-Chip des Raspberry Pi 3B während seines aktiven APs andere Netze nicht zuverlässig scannt, bleibt die manuelle SSID-Eingabe ausdrücklich verfügbar.

### Dauerhafte Support-Diagnose

Das Image speichert systemd-Journale begrenzt und komprimiert über mehrere Boots. First Boot und Dienstfehler erzeugen automatisch ein geschwärztes Support-Paket; unter **System → Support-Datei erstellen** kann jederzeit ein aktuelles Paket angefordert und heruntergeladen werden. Bei einer Fehlermeldung wird immer `Grow-Central-Support-latest.tar.gz` benötigt. Passwörter, Tokens, Cookies, PSKs und Hashwerte werden entfernt; technische Netzwerk- und Hardwarekennungen bleiben für die Analyse enthalten.

### Heimnetzwerk und FRITZ!SmartHome

Die lokale GUI besitzt einen eigenen Bereich **Netzwerk**. Dort können aktive Schnittstellen angezeigt, WLAN-Netze gesucht und der Pi nachträglich mit einem WLAN verbunden werden. Scan, kein Treffer, Timeout und Fehler werden sichtbar zurückgemeldet.

Grow Central prüft nach dem GUI-Start auf eine eindeutig erkennbare FRITZ!Box. Wird eine Box erkannt, fordert die GUI einen FRITZ!Box-Benutzer an. Nach erfolgreichem Login werden über die lokale AVM/AHA-Schnittstelle unterstützte FRITZ!SmartHome-Schaltgeräte importiert und in der gemeinsamen Strom-/Geräteansicht bereitgestellt. Der aktuelle native Adapter unterstützt bei passenden FRITZ!-Geräten:

- erreichbar / offline;
- Schaltzustand;
- Ein / Aus;
- aktuelle Leistung in W;
- Gesamtenergie in Wh/kWh;
- Gerätename und AIN.

Reale Funktion und Messwerte müssen gegen die jeweilige FRITZ!Box-/Steckdosen-Kombination bestätigt werden.

### TP-Link Tapo

Tapo bleibt als **hybride Integration** vorgesehen: lokale Gerätekommunikation wird im Heimnetz bevorzugt; der Tapo/TP-Link-Account bleibt Grundlage für authentifizierte Gerätezuordnung und die bestehende WAN-Fähigkeit des Tapo-Ökosystems soll nicht verloren gehen. Der aktuelle Grow-Central-Adapter implementiert den lokalen authentifizierten `python-kasa`-Pfad. Ein eigener validierter Grow-Central-WAN/Cloud-Transport wird nicht vorgetäuscht und bleibt separat zu implementieren und zu testen.

### Logitech C920 / UVC-Kameras

Die **Logitech C920 ist die Referenzkamera und für den aktuellen Hardwaretest direkt am Raspberry Pi angeschlossen**. `alpha-0.7.5` enthält einen sichtbaren Bereich **Kamera**:

- Erkennung der vorhandenen `/dev/video*`-Geräte;
- Kennzeichnung einer erkannten Logitech C920;
- Anzeige von Lesbarkeit und Capture-Fähigkeit;
- echter JPEG-Test-Snapshot über `ffmpeg`;
- dynamisches Bedienfeld aus den tatsächlich von der Kamera gemeldeten V4L2-Reglern;
- z. B. Helligkeit, Kontrast, Sättigung, Weißabgleich, Belichtung, Fokus, Zoom oder weitere Regler – **nur wenn die jeweilige Kamera sie meldet**;
- Wertebereichs-/Menüvalidierung vor Änderungen;
- Audit-Eintrag für Kamera-Control-Änderungen.

Die Browseroberfläche darf weder einen beliebigen `/dev/video*`-Pfad noch einen unbekannten V4L2-Controlnamen an den Server durchreichen.

### Mars Hydro

| Gerät | Projektdefinition | Integrationsrichtung |
|---|---|---|
| **Mars Hydro FC3000** | Modelljahr **2024**, USB-Port, **iConnect** | gemeinsame Mars-Hydro/iConnect-Gerätefamilie |
| **Mars Hydro DF100 / iFresh** | iFresh-Serie mit **iConnect** | gemeinsame Mars-Hydro/iConnect-Gerätefamilie |
| **DF100M / MZ_MZF002** | beobachteter BLE-Pfad | experimentelle Diagnose / Reverse Engineering / Fallback |

Bluetooth-Discovery und Kommunikation sind im aktuellen Hardwaretest grundsätzlich funktionsfähig beobachtet worden. Unbekannte Mars-Hydro-Schreibtelegramme bleiben weiterhin gesperrt, bis sie auf realer Zielhardware reproduzierbar validiert wurden.

### Sicherheitsmodell

- Smart-Home-Code bleibt standardmäßig **deny-by-default**; das Appliance-Image aktiviert die Integration explizit.
- Schreiboperationen benötigen eine authentifizierte Grow-Central-GUI-Sitzung oder ein explizites API-Token.
- Geräte müssen bekannt, freigegeben und beschreibbar sein.
- GUI-Passwörter werden als PBKDF2-SHA256-Verifier gespeichert, nicht im Klartext.
- Integrationspasswörter werden nicht über Browser-APIs zurückgegeben und nicht absichtlich geloggt.
- Der öffentliche Webauftritt besitzt keine lokalen Gerätezugangsdaten oder direkten Steuerendpunkte.
- Ein späterer WAN-Zugriff auf die Grow-Central-GUI muss zusätzlich über TLS/HTTPS bzw. einen abgesicherten Reverse-Proxy/VPN erfolgen; ein Login allein ersetzt keine Transportverschlüsselung.

### Architektur

```text
Clients im LAN / später abgesicherter Remote-Zugang
                         │
                  GUI Login / Session
                         │
                         ▼
              135er-Grow Central Local
                    Raspberry Pi 3B
        ┌────────────────┼─────────────────┐
        │                │                 │
   Mars Hydro       Smart Home          Kamera
 FC3000/iFresh   FRITZ!/Tapo/Shelly   C920 / UVC
        │                │                 │
  BLE/iConnect      local APIs          V4L2
 diagnostics         + policy           ffmpeg
```

**ESP32 ist nicht Bestandteil der Zielarchitektur.**

Weiterlesen: [Integrationen](docs/de/INTEGRATIONEN.md) · [Mars Hydro / iConnect](docs/MARS_HYDRO_ICONNECT.md) · [Hardware-Testplan](docs/HARDWARE_TEST_PLAN.md) · [Raspberry-Pi-Testimage](docs/de/RASPBERRY_PI_3B_TEST_IMAGE.md)

---

## English

**135er-Grow Central alpha-0.7.5** is a local-first Raspberry Pi 3B control platform. The current release line adds a mandatory first-boot password change, LAN detection/WLAN selection, optional dedicated FRITZ!Box Smart Home credentials, mandatory GUI credentials and authenticated GUI sessions.

The GUI now includes post-setup network management, automatic FRITZ!Box presence detection/login/import and a directly testable Logitech C920/UVC camera panel with device detection, JPEG snapshots and dynamically generated V4L2 controls. Smart-home writes remain deny-by-default in source and are explicitly enabled by the appliance image behind authentication and per-device approval/write gates.

Tapo remains a hybrid local/WAN design goal. The current adapter implements authenticated local device access; a Grow-Central WAN transport must still be implemented and validated rather than assumed.

Mars Hydro targets remain **FC3000 2024 (USB + iConnect)** and **iFresh/DF100 (iConnect)** as one ecosystem, with DF100M BLE retained for diagnostics/reverse engineering/fallback.

Continue with: [English documentation](docs/en/README.md) · [Integrations](docs/en/INTEGRATIONS.md) · [Hardware test plan](docs/HARDWARE_TEST_PLAN.md)

## Interface family / Interface-Familie

<table>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-desktop-v0.9.png" alt="135er-Grow Central local desktop interface"><br><strong>Local Desktop</strong></td>
    <td width="50%"><img src="website/assets/gui/local-tablet-v0.9.png" alt="135er-Grow Central local tablet interface"><br><strong>Local Tablet</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-mobile-v0.9.png" alt="135er-Grow Central local mobile interface"><br><strong>Local Mobile</strong></td>
    <td width="50%"><img src="website/assets/gui/cloud-desktop-v0.9.png" alt="135er-Grow Central optional cloud interface"><br><strong>Cloud Desktop</strong></td>
  </tr>
</table>

> [!NOTE]
> GUI preview values are concept telemetry unless explicitly marked as hardware-validated.

<p align="center"><img src="website/assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central · J.L." width="760"></p>
