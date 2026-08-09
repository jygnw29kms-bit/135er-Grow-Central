# DF100M Research Log

## Scope

Reverse engineering of Mars Hydro DF100M / MZ_MZF002 behavior for local Raspberry Pi integration. This file records evidence levels and prevents guesses from becoming protocol facts.

## Evidence labels

- `official`: manufacturer statement/documentation.
- `apk-observation`: observed in Legacy application package/resources/code strings.
- `candidate`: plausible but not hardware-confirmed.
- `observed`: captured from real target device/session.
- `replayed`: sent back and produced repeatable behavior.
- `validated`: repeated tests support use as implemented protocol behavior.

## Target device

```text
Identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID:  A0A3B35EFDC8
Firmware:   V1.8
```

## Legacy app observations

Strings of interest:

```text
MZ_MZF
MZ_MZF002
Fan type
Wind Speed
wind_speed
wind_speed_num
wind_set_speed
wind_save_enable
RPM
flutter_reactive_ble
discoverServices
writeCharacteristicWithResponse
NotifyCharacteristicRequest
```

These indicate BLE/GATT interaction and fan-speed semantics but do not by themselves define packet layout.

## Candidate UUIDs

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e
83677baa-3eb8-4866-b6b6-96e5ed5cc48d
f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

Current status: `candidate` until real service/characteristic mapping is captured.

## Legacy API observations

Observed base:

```text
https://api.lgledsolutions.com/
```

Observed endpoint strings include:

```text
api/ios/udm/getDeviceList/v1
api/ios/udm/getAllDevice/v1
api/ios/udm/getDeviceDetail/v1
api/ios/dnet/configWifi/v1
api/ios/dnet/getMeshKey/v1
api/ios/dcs/getSyncCommand/v1
api/ios/dua/getDeviceUpStatus/v1
api/ios/dua/upDevice/v2
api/ios/udm/editDevice/v1
api/ios/udm/subDeviceSwitch/v1
api/ios/udm/lampSwitch/v1
```

These are reverse-engineering observations, not official API documentation and not required for the local-first BLE path unless future research proves otherwise.

## Experimental payload modes currently represented in local runtime

```text
byte      -> bytes([percent])
ascii     -> ASCII percent
hexprefix -> [0x01, percent]
```

All are hypotheses until validated.

## Hardware validation procedure

1. Close/kill Mars Legacy so the BLE connection is released.
2. Scan using `bluetoothctl` and Grow Central discovery.
3. Identify target device by advertisement/name/address evidence.
4. Connect and dump GATT services/characteristics.
5. Start notifications without writes.
6. Re-open controlled Legacy session where necessary and record behavior at 10/30/50/70/90 %.
7. Correlate changed bytes/notifications with commanded values.
8. Record candidate write characteristic and payload.
9. Replay only with safe bounds and explicit write enable.
10. Repeat multiple values and disconnect/reconnect cycles.

## Validation table

| Item | Current level |
|---|---|
| Device identity | observed from Legacy context |
| Firmware V1.8 | observed |
| BLE library usage in Legacy | apk-observation |
| Candidate UUID set | candidate |
| Notify characteristic | candidate |
| Write characteristic | candidate |
| Speed packet layout | candidate |
| RPM decode | not established |
| Reliable percentage control | not validated |

## Safety rule

No documentation or UI may present DF100M control as validated until a real-device test moves the relevant findings through `observed → replayed → validated`.
