# Mars Legacy 1.2.2: statische Android-XAPK-Analyse (13.11.2026)

## Material und Vorgehen

Vom Eigentümer bereitgestellte Datei `Mars+Legacy_1.2.2_APKPure.xapk` (rund 27 MB), SHA-256:
`f570bb8cf331b499cd36255ce219f3be20dcf0715239730aed0efefbbc390e19`

Die XAPK ist ein ZIP-Container mit Haupt-APK `com.mz.mziot.apk` (19.748.987 Bytes), ARM64-Split-APK (`config.arm64_v8a.apk`) und Sprach-/Grafik-Splits. Die Flutter-App enthält im ARM64-Split `lib/arm64-v8a/libapp.so` (7.340.976 Bytes). Statische Analyse des eingebetteten Flutter-AOT-Snapshots mit dem Unix-`strings`-Werkzeug. Es wurde keine App gestartet, keine Geräte- oder Cloud-Anmeldung vorgenommen und kein BLE-Kommando gesendet.

## Direkte Treffer aus der Original-Anwendung

| Original-String | Bedeutung / Bezug |
| --- | --- |
| `MZ_MZF`, `MZ_MARS` | Beide lokal erkannte Bluetooth-Gerätefamilien |
| `83677baa-3eb8-4866-b6b6-96e5ed5cc48d` | Gleiche Service-UUID wie am echten DF150-M/FC3000 |
| `6f588463-f8f1-44f8-bdae-a1272a1b0f6e` | Identische Notify-Characteristic wie am Grow-Pi |
| `f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d` | Identische Write-Characteristic wie am Grow-Pi |
| `wind_set_speed`, `wind_speed_num`, `wind_speed_rate`, `wind_mode`, `wind_pressure` | Hersteller-App besitzt explizite Lüftersteuerungs-/Telemetriebegriffe |
| `api/ios/udm/adjustLight/v1`, `api/ios/udm/lampSwitch/v1`, `api/ios/udm/subDeviceSwitch/v1` | REST-Routen für steuernde Funktionen in der *Android*-Flutter-App (Benennung `ios` im Pfad) |
| `api/ios/dnet/getMeshKey/v1`, `api/ios/dnet/configWifi/v1` | Möglicher Mesh-Key-/WiFi-Provisioning-Ablauf |
| `api/ios/tlogin/unionLogin/v1` | Externer/vereinigter Login-Pfad; unterstützt die Suche nach Apple-Sign-in-Anmeldung, beweist deren Ablauf aber nicht |
| `writeCharacteristicWithResponse` | Einbindung einer GATT-Schreibschnittstelle im Flutter-Bundle |

**Wichtig:** Ein String-Beleg zeigt nur, dass die App diesen Namen referenziert. Er zeigt weder die nötigen Argumente noch eine gültige GATT-Payload oder konkrete Netzwerkanfrage.

## Neue Erkenntnisse in Verbindung mit vorhandenen Mitschnitten

1. Der eigenständige lokale BLE-Leseweg zum MZF002 ist eindeutig derselbe Protokollbereich wie in der Original-App (Service + Notify + Write deckungsgleich).
2. Lüfterregelung ist appseitig als `wind_set_speed` erkennbar; ob diese Aktion über REST, WLAN, BLE oder eine Kombination läuft, lässt sich aus Strings allein nicht entscheiden.
3. Die in der App vorhandene Route `getMeshKey` eröffnet eine konkrete Prüfspur für die gemeinsame Kennung `68756`. Der Inhalt/Verwendungszweck des Schlüssels bleibt unbekannt. Kein Herunterladen, Publizieren oder Hardcodieren von Auth-Schlüsseln.
4. Die private iPhone-HCI-Aufzeichnung lieferte 266 MZF002-Status-Notifications, aber keine ATT-Writes während der Lüfter-Stufenwechsel. Das passt zu einer alternativen Steuerroute, beweist aber nicht, dass BLE-Schreiben generell ungenutzt ist.
5. Der Nutzer verwendet Apple-Anmeldung. E-Mail/Passwort-Cloudintegration ist daher keine geeignete Voraussetzung und bleibt deaktiviert.

## Weiteres Vorgehen

- Falls nötig Flutter-AOT-Analyse / dynamische, autorisierte Beobachtung an einer lokalen Test-App durchführen, um **genau** die Funktion hinter `wind_set_speed` und ihren Aufrufpfad zu bestimmen.
- Keine zufälligen GATT-Write-Nutzlasten schicken; zuerst Payload aus einer erfolgreichen eigenen Sitzung oder veröffentlichter kompatibler Implementierung validieren.
- Für einen Einzel-Hardwaretest gelten Gerätebindung, ausdrücklicher Klick, Status-Rücklesen, Zeitlimit und keine automatische Wiederholung.
- Nichts davon benötigt Eingriffe am Router oder Apple-Konto.

**Stand:** App-Ursprung und eindeutige Protokollstrings verifiziert; Write-Payload nicht extrahiert, reale DF150-M-Steuerung durch Grow Central weiterhin nicht bestätigt.
