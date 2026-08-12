# DF100M BLE Diagnostics / Reverse Engineering

## Rolle im Projekt

Dieser Pfad ist **nicht mehr die primäre Mars-Hydro-Architektur**.

Verbindliche Zielhardware:

- **Mars Hydro FC3000, Modelljahr 2024, USB-Port, iConnect-Unterstützung**
- **Mars Hydro iFresh / DF100-Serie mit iConnect**

Beide werden zukünftig über eine gemeinsame Mars-Hydro/iConnect-Abstraktionsschicht modelliert. Der hier dokumentierte DF100M-/BLE-Pfad bleibt als Diagnose-, Reverse-Engineering- und Fallback-Werkzeug erhalten, solange kein reproduzierbar validierter lokaler iConnect-Pfad dokumentiert ist.

## Ziel des BLE-Pfads

Das Ziel ist nicht, blind Kommandos zu erraten, sondern aus dem realen Gerät eine reproduzierbare Protokollbeschreibung zu erzeugen.

## Beobachtetes Gerät

```text
Mars Hydro DF100M
Family / BLE identity: MZ_MZF002
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

1. Zielgerät einschalten.
2. Mars-Hydro-App/iConnect-Verbindung vollständig trennen, falls sie BLE exklusiv belegt.
3. `DISCOVER` im Webinterface ausführen.
4. Gerätename und BLE-Adresse dokumentieren.

### Stufe B – GATT

1. Verbindung herstellen.
2. `READ GATT` ausführen.
3. Services und Characteristics speichern.
4. Properties notieren: `read`, `write`, `write-without-response`, `notify`, `indicate`.

### Stufe C – Vergleich

Für genau einen Parameter mehrere bekannte Werte setzen und den beobachtbaren Traffic vergleichen. Es werden keine unbekannten Writes vom Pi gesendet, bevor das Muster aus realem Verhalten abgeleitet wurde.

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

Erst nachdem das Muster bekannt ist, denselben Befehl kontrolliert vom Raspberry Pi senden. Schreibzugriffe bleiben bis dahin deaktiviert.

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

## Sicherheitsvorgabe

```text
DF100M_ALLOW_WRITES=false
DF100M_ALLOW_RAW_WRITES=false
```

Die Variablen dürfen im normalen Betrieb nicht automatisch aktiviert werden.

## Quellen und Architektur

Siehe [SOURCES.md](SOURCES.md) und [MARS_HYDRO_ICONNECT.md](MARS_HYDRO_ICONNECT.md).
