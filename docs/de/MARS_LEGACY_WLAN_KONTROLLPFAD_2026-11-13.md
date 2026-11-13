# Mars Legacy 1.2.2: WLAN-Kontrollpfad (Analyse 13.11.2026)

## Nachgewiesen am eigenen Aufbau

- **Zwei eigenständige WLAN-Funkmodule** senden jeweils `MZ-AP-MASTER-68756` (Kanal 11, WPA2) mit verschiedenen BSSIDs: DF150-M-Kandidat `A0:A3:B3:5E:FD:C9`, FC3000-Kandidat `FC:B4:67:AE:C2:61`.
- Der Pi bleibt per Ethernet verbunden; WLAN `wlan0` ist **nicht** mit den Geräte-APs verbunden. Passiver `nmcli --rescan no`-Scan und `GET /api/mars-hydro/ble/wifi-access-points` funktionieren ohne Netzwerkumbau.
- Zum Lüfter besteht eine **echte BLE-Verbindung**. GATT-Notify liefert 23-Felder-Status mit Ein/Aus, 25–100%-Sollwert, RPM, Temperatur und rF.
- Der private iPhone-HCI-Mitschnitt aus dem Stufenversuch enthält **266** MZF002-Notifications, aber **keine BLE-ATT-Writes** bei den Lüfteränderungen. Der Steuerweg dieser App-Sitzung wurde damit nicht über iPhone-BLE-Write beobachtet.

## Original-Android-App (nutzerbereitgestellte XAPK)

SHA256: `f570bb8cf331b499cd36255ce219f3be20dcf0715239730aed0efefbbc390e19`. Haupt-APK mit Flutter ARM64 AOT `libapp.so` (7.340.976 Byte). Offline untersucht, nichts ausgeführt.

Verifizierte Strings:

- `Setup WiFi to enable remote control`
- `Connecting WiFi can enable remote control. Are you sure to skip?`
- `api/ios/dnet/configWifi/v1`
- `api/ios/dnet/getMeshKey/v1`
- `wind_set_speed`, `wind_mode`, `wind_speed_num`
- `api/ios/udm/adjustLight/v1`, `api/ios/udm/lampSwitch/v1`, `api/ios/udm/subDeviceSwitch/v1`
- Die in der Pi-Hardware identifizierten BLE-Service-/Notify-/Write-UUIDs
- `api/ios/tlogin/unionLogin/v1` als möglicher externer Login-Endpunkt

Wichtig: Diese Strings weisen auf vorhandene Funktionalität hin, **belegen aber weder den tatsächlich ausgeführten Aufrufpfad noch eine lokale HTTP-/UDP-Steuerung**. `getMeshKey` beweist keinen bekannten/zugänglichen Mesh-Schlüssel. App-Store-Apple-Sign-in beweist keinen nutzbaren E-Mail/Passwort-Zugang.

Reproduzierbare erneute Prüfung der XAPK:

```bash
python3 scripts/mars_legacy_wifi_apk_audit.py '/PFAD/ZUR/Mars+Legacy_1.2.2_APKPure.xapk'
```

Ausgabe enthält nur Marker-Präsenz, Prüfsumme und Redaktions-/Kontrollstatus; **keine Auth-Tokens oder Schlüssel**.

## Öffentlich dokumentierte Gegenprobe (mit Einschränkung)

- Mars Hydro beschreibt offiziell sowohl WLAN- als auch Bluetooth-Steuerung: https://www.mars-hydro.com/mars-hydro-app
- GrowVPD Pro dokumentiert für eigene iConnect-Integration: BLE zur WLAN-Provisionierung, anschließend WLAN plus Mars-Hydro-Cloud für Fernsteuerung. **Die Inline-Lüftersteuerung ist dort explizit als implementiert, aber noch nicht realhardware-verifiziert ausgewiesen.** https://growvpd.pro/guides/connect-mars-hydro
- Der Benutzer hat **ausschließlich „Mit Apple anmelden“**. Eine Login/Passwort-only-Cloudlösung ersetzt daher nicht die lokale Steuerung und ist in GC nicht automatisch zu aktivieren.

## Schlussfolgerungen und Grenzen

Der wahrscheinlichste ursprüngliche App-Ablauf ist *BLE-Discovery/Pairing → WLAN-Provisionierung/Cloudbindung → Sollwert-Befehl über Cloud/Netzwerk → BLE-/Gerätestatus*. Das passt zum fehlenden ATT-Write während der iPhone-Lüfterbedienung, ist aber **nicht direkt durch einen Paketmitschnitt des tatsächlichen Cloud-/WLAN-Befehls bewiesen**.

**AP-SSID/BSSID allein** bedeutet weder, dass das Gerät mit dem heimischen WLAN verbunden ist, noch dass es einen lokalen Steuerport anbietet. Kein Router-Check/-Reset, keine WiFi-Passwortsuche, kein ungebetener Re-Pairing-Versuch oder Token-Replay.

## Konkrete nächste Nachweise

1. Auf der bereits autorisierten Umgebung **nur Metadaten** einer eigenen App-Steueraktion im WLAN-Pfad erfassen (Ziel-IP/-Port, TLS-Verbindung vs. lokale Ziel-IP); keine Login-/Apple-Tokens publik machen.
2. Falls Cloud-Ziel bestätigt: festhalten, dass der Weg nicht lokal und ohne bestehende Apple-Session nicht nutzbar ist. Separate GATT-Lokalsteuerung weiter untersuchen.
3. Falls lokale Geräte-IP bestätigt: ausschließlich für identifizierte, eigene Geräte mit dokumentiertem Port gezielte, zunächst **lesende** Prüfung durchführen.
4. Echte Hardwaresteuerung erst nach exakt bestätigter Payload und Geräte-Rückmeldung aktivieren. Kein ungeprüftes Schreiben.
