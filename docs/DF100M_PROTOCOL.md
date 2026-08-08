# DF100M Reverse Engineering

## Ziel

Das Ziel ist nicht, blind Kommandos zu erraten, sondern aus dem realen Gerät eine reproduzierbare Protokollbeschreibung zu erzeugen.

## Gerät aus dem Projekt

```text
Mars Hydro DF100M
Family: MZ_MZF002
Observed firmware: V1.8
```

## Ausgangsinformationen

`[APK-OBSERVATION]`

Gefundene Begriffe:

```text
MZ_MZF
wind_set_speed
wind_speed
wind_speed_num
RPM
flutter_reactive_ble
writeCharacteristicWithResponse
NotifyCharacteristicRequest
```

UUID-Kandidaten:

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e
83677baa-3eb8-4866-b6b6-96e5ed5cc48d
f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

## Testablauf

### Stufe A – Discovery

1. DF100M einschalten.
2. Mars Legacy vollständig schließen.
3. `DISCOVER` im Webinterface ausführen.
4. Gerätename und BLE-Adresse dokumentieren.

### Stufe B – GATT

1. Verbindung herstellen.
2. `READ GATT` ausführen.
3. Services und Characteristics speichern.
4. Properties notieren:
   - read
   - write
   - write-without-response
   - notify
   - indicate

### Stufe C – Vergleich mit Legacy

Für genau einen Parameter mehrere bekannte Werte setzen:

```text
10 %
30 %
50 %
70 %
90 %
```

Dazu jeweils das BLE-Paket erfassen.

### Stufe D – Muster bestimmen

Zu prüfen:

- einzelnes Byte?
- Fan-Stufe statt Prozent?
- Little-/Big-Endian?
- JSON/String?
- Binärframe?
- Header?
- Checksumme?
- Counter/Sequence?
- Device-ID im Payload?

### Stufe E – Replay

Erst nachdem das Muster bekannt ist, denselben Befehl vom Raspberry Pi senden.

## Protokolltabelle

| Funktion | Characteristic | Request | Response | Status |
|---|---|---|---|---|
| Connect | TBD | TBD | TBD | offen |
| Status | TBD | TBD | TBD | offen |
| Fan Speed | TBD | TBD | TBD | offen |
| Power | TBD | TBD | TBD | offen |
| RPM | TBD | TBD | TBD | offen |

## Statusdefinition

- **offen** – noch nicht untersucht
- **candidate** – technisch plausibel
- **observed** – im App-Traffic beobachtet
- **replayed** – vom Pi erfolgreich wiederholt
- **validated** – mehrfach reproduziert und Status bestätigt

## Quellen

Siehe [SOURCES.md](SOURCES.md).
