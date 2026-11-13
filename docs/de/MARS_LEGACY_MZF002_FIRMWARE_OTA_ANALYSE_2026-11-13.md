# MZF002 / DF150-M: Firmware-OTA-Recherche (2026-11-13)

## Ergebnis

Für **genau MZF002/DF150-M** ist derzeit **kein öffentlich downloadbares Original-Firmware-Binärpaket (.bin/.ota/.fw)** verifiziert. Die Herstellerseite führt Handbücher, keine eindeutig zuordenbare Firmwaredatei. Laut Mars Hydro werden Updates offiziell **über die App**, bei bereits eingerichteter WLAN-Verbindung und teils automatisch bei der ersten Netzwerkkopplung, ausgeliefert.

Dokumentation: https://www.mars-hydro.com/faq/question/id/220 und https://www.mars-hydro.com/user-manuals-download

## Statische Prüfung der vom Benutzer gelieferten XAPK

Datei: `Mars+Legacy_1.2.2_APKPure.xapk`
SHA256: `f570bb8cf331b499cd36255ce219f3be20dcf0715239730aed0efefbbc390e19`

Im Flutter-AOT-Modul `lib/arm64-v8a/libapp.so` (7.340.976 Bytes) sind die folgenden **exakten** Strings enthalten:

- `api/ios/udm/getUpgradeProduct/v1`
- `api/ios/udm/getUpgradeCommand/v1`
- `downLoadUrl`
- `upgradeData`
- `api/ios/dnet/configWifi/v1`
- `api/ios/dnet/getMeshKey/v1`
- `wind_set_speed`

**Interpretation:** Die App besitzt eine OTA-Produkt-/Firmware-Abfragelogik und ein Datenfeld für einen Download-Link. Die Verfügbarkeit eines Firmwarepakets für eine konkrete Seriennummer setzt aber vermutlich eine authentifizierte Geräte-/Versionsabfrage voraus. Weder das URL-Ziel noch ein für MZF002 bestimmtes Firmwareimage sind allein durch die Strings bekannt. `getUpgradeCommand` nicht blind aufrufen: Es könnte ein Upgrade anstoßen.

In allen eingebetteten APK-Splits wurde **kein eindeutig benanntes, eigenständiges Geräte-Firmwareimage** gefunden. `DebugProbesKt.bin` und `AssetManifest.bin` sind App-Ressourcen, keine MZF002-Firmware.

## Sicheres Vorgehen

1. Hardware/aktuelle Revision nur über vorhandene, dekodierte BLE-Statusinformationen prüfen (MZF002 in früheren Originalmeldungen: Firmware 1.8; aktuelle Geräteversion vor Upgrade neu ermitteln).
2. Bei einer ausdrücklich erlaubten Hersteller-App-Update-Prüfung **nur** die Metadaten und eigentliche Download-URL einer angezeigten Firmware sichern, ohne auf „Upgrade starten“ zu drücken.
3. Ein Firmwareimage erst nach Herkunfts-, Größen- und SHA-256-Prüfung offline mit Binwalk/Strings/Disassembler untersuchen.
4. Vor Geräteoperationen keine Firmware flashen, keine WLAN-Passwörter erraten und keine generischen FC3000-Kommandos auf den DF150-M übertragen.
5. Aus dem Firmwarepaket ggf. Befehlsstruktur, Netzwerkkonfiguration und Dienste bestimmen; danach mit der vorhandenen Original-App und BLE-Messreihe vergleichen.

Automatisches Offline-Werkzeug im Repository: `scripts/mars_legacy_firmware_audit.py`.

**Stand:** OTA-Routen und Download-Link-Feld in Original-App bestätigt. Keine originale DF150-M-Firmware öffentlich gefunden, keine Firmware heruntergeladen, kein Geräteupdate ausgelöst.
