# 135er-Grow Central

<p align="center"><img src="website/assets/brand/135er-grow-central-logo.svg" alt="135er-Grow Central Logo" width="720"></p>
<p align="center"><strong>LOCAL-FIRST · RASPBERRY PI · SMART HOME · POWER TELEMETRY</strong></p>
<p align="center"><code>🚧 WORK IN PROGRESS</code> &nbsp; <code>v0.8 development</code> &nbsp; <code>deny-by-default writes</code></p>

> [!WARNING]
> **Work in Progress:** Hardware- und Protokollpfade werden weiter validiert. Der Raspberry Pi bleibt die lokale Autorität; optionale Cloud-Funktionen ersetzen die lokale Steuerung nicht.

## Vier GUI-Clients · ein Design

![Local Desktop](website/assets/gui/local-desktop-v0.8.svg)
![Local Tablet](website/assets/gui/local-tablet-v0.8.svg)
![Local Mobile](website/assets/gui/local-mobile-v0.8.svg)
![Cloud Desktop](website/assets/gui/cloud-desktop-v0.8.svg)

## Architektur

```text
Geräte / Sensoren / Smart Plugs
            |
            v
   135er-Grow Central Local
        Raspberry Pi
       /     |      \
  BLE DF100M |       Shelly RPC
             |
           SQLite
             | outbound HTTPS
             v
       optional cloud
```

## Branding
- Logo: `website/assets/brand/135er-grow-central-logo.svg`
- Markenzeichen: `website/assets/brand/135er-grow-central-mark.svg`
- Logo dominant; Markenzeichen klein und dauerhaft sichtbar.
- Kein WebP.

## Raspberry Pi
Bootlogo und ASCII-Konsolenbegrüßung werden im Image-Build eingebunden.
