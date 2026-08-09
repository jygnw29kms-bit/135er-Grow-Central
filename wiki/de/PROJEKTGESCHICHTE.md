# Projektgeschichte

135er-Grow Central begann als konkrete Raspberry-Pi-Lösung für einen Mars Hydro DF100M, weil im vorhandenen Setup die Mars Legacy App funktionierte, die neuere Mars-Hydro-App jedoch nicht zuverlässig nutzbar war.

## Entwicklungslinie

1. **Lokale Geräteidee:** DF100M ohne permanente Hersteller-App lokal erkennen und später steuern.
2. **Raspberry Pi als Master:** bewusste Entscheidung gegen eine ESP32-Core-Architektur.
3. **Legacy-App-Analyse:** Identifikation von BLE/GATT-Hinweisen, Fan-/Speed-Begriffen und Kandidaten-UUIDs.
4. **FastAPI/Bleak-Prototyp:** Discovery, Connect/Disconnect, GATT-Inspektion und Notifications.
5. **Write-Safety:** experimentelle Payloadmodi vorhanden, aber standardmäßig deaktiviert.
6. **Future-HUD:** dunkle responsive Browseroberfläche als Designziel.
7. **Local-first Cloud:** optionaler VPS für Telemetrie, Historie und Remote-Übersicht; Pi bleibt Master.
8. **Full Platform v0.5:** Datenmodell für Benutzer/RBAC, Sites, Geräte, Sensoren, Historie, Zeitpläne, Automationen, Events, Alerts, Commands, Audit und Backups.
9. **GitHub-Konsolidierung:** Repository wird zur führenden Quelle; Wiki wird im Hauptrepo versioniert.
10. **Hardware-Testimage:** reproduzierbarer CI-Build für Raspberry Pi 3B/3B+.
11. **Nächster Schritt:** reale DF100M-GATT-/Notification-Captures und kontrollierte Protokollvalidierung.

## Testgerät

```text
Identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID: A0A3B35EFDC8
Firmware: V1.8
```

## Build-Erfahrungen

Der erste Imagebuild lief wegen versehentlich mitkopierter Build-Images in ein volles Root-Dateisystem. Der zweite Build kam bis zur UFW-Initialisierung; diese scheiterte im ARM-chroot an der iptables-Erkennung. Der aktuelle Builder vergrößert die Root-Partition, schließt Buildartefakte aus und aktiviert UFW erst beim ersten echten Raspberry-Pi-Boot.

Ausführlicher Verlauf: `PROJECT_HISTORY.md` im Hauptrepository.
