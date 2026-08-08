# DF100M Protokollanalyse

Die Daten in diesem Abschnitt sind Reverse-Engineering-Anhaltspunkte.

## APK-Beobachtungen

```text
MZ_MZF
MZ_MZF002
wind_speed
wind_speed_num
wind_set_speed
RPM
flutter_reactive_ble
writeCharacteristicWithResponse
NotifyCharacteristicRequest
```

## UUID-Kandidaten

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e
83677baa-3eb8-4866-b6b6-96e5ed5cc48d
f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

## Validierung

`candidate → observed → replayed → validated`

Schreibzugriffe bleiben bis zur Validierung standardmäßig deaktiviert.
