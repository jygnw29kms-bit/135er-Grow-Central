# FC 3000 zuerst: Mars-Legacy-BLE-Entwicklungsblock

**Aktiver Umfang:** nur die Mars Hydro FC 3000. Der Lüfter bleibt unverändert und außerhalb aller FC3000-Auswertungen.

## Gerätebefund (Stand 2026-11-12)

- Der Pi hat bei früheren Scans einen Licht-Kandidaten mit dem Namensmuster `MZ_MARS_...C260` gesehen. Er ist **noch nicht** durch einen kontrollierten Vor-Ort-Abgleich der FC 3000 zugeordnet.
- `MZ_MZF002` und seine bestätigten UUIDs gehören zum **Lüfterkandidaten**. Diese UUIDs dürfen nicht ohne eigenen Nachweis als FC3000-Befehle verwendet werden.
- Die Mars-Legacy-App beansprucht laut Anwender die jeweils einzige aktive Steuerverbindung des Zielgeräts. Kein gleichzeitiges GATT-Inspect via Pi, solange das iPhone verbunden ist.
- Ein normaler Pi-HCI-Mitschnitt (`btmon`) enthält keine fremde iPhone-FC3000-Verbindung. Für die direkte Untersuchung ist ein geeigneter RF-Sniffer beziehungsweise eine andere tatsächlich zugängliche Quelle bereits entschlüsselter ATT-Nutzdaten erforderlich.
- **Keine bestätigten Ein/Aus- oder Dimm-Bytes** und keine Freigabe für Geräteschreibzugriffe.

## Prüfschritte

1. FC 3000 anhand des Advertising-Musters und ihrer alleinigen, kontrollierten Anwesenheit identifizieren. Die Gerätebezeichnung `C260` allein genügt nicht.
2. Vor jedem Versuch die aktive BLE-Verbindung der Legacy-App berücksichtigen. Passiv mit geeigneter Hardware mitschneiden, nicht auf dem Pi parallel verbinden.
3. Eine kurze Legacy-Sitzung der Lampe erfassen: `idle`, `light_on`, `light_off`, `dim_25`, `dim_50`, `dim_75`, `dim_100`, nur wenn der jeweilige Wert in der App angeboten wird. Jede Aktion mit Zeitstempel und physisch beobachtetem Zustand dokumentieren.
4. Bereits dekodierte ATT-Daten nach dem in `MARS_LEGACY_BLE_MITSCHNITT.md` beschriebenen CSV-Schema bereitstellen. Unbekannte Payloads, BLE-Adressen und Schlüssel ausschließlich privat speichern.
5. Action-Windows in JSONL umwandeln und ausschließlich Lampen-Daten auswerten:

```bash
python3 scripts/mars_legacy_windows.py capture.csv windows.csv labelled.jsonl
python3 scripts/fc3000_legacy_offline_audit.py labelled.jsonl --output fc3000_candidates.json
python3 -m unittest discover -s tests -p 'test_fc3000_legacy_offline_audit.py'
```

Alle `device`-Werte müssen `lamp` lauten; jede `session` braucht eine eigene Kennung. Fan-Daten und andere Aktionen werden bewusst verworfen. Ausgabe enthält **nur Kandidaten**, auch bei mehrfach gleichen Payloads; `validated_command_count=0` bis zur echten Hardwareabnahme.

## Abnahmekriterien

Eine Steuerfunktion darf erst freigeschaltet werden, nachdem das exakt verwendete Lampenmodell mitsamt Firmware identifiziert, die zugehörige BLE-Characteristic tatsächlich am Lampengerät gelesen, die Befehlsfolge in mehreren unabhängigen Sitzungen aufgezeichnet und ihre physische Wirkung überprüft wurde. Keine unbestätigten Raw-Hex-Write-Endpunkte.

**Bekannte Einschränkung:** Das Offline-Skript importiert bereits dekodierte ATT-Nachrichten. Es beschafft weder BLE-Pairing-Schlüssel noch entschlüsselt es fremde Funkverbindungen. Die eigentliche Original-App-Aufzeichnung steht noch aus.

## Bestätigung durch Mars-Legacy-iPhone-Screenshots (2026-11-12, 18:05 lokal)

- **FC 3000** wird in Mars Legacy mit Geräte-ID **`FCB467AEC260`** angezeigt.
- Auf der Geräteseite steht **Firmware V3.4**.
- Der Anwender bestätigt, mit der **FC 3000** erfolgreich per iPhone verbunden zu sein und sie steuern zu können.
- Der auf dem Pi früher beobachtete Advertising-Kandidat `MZ_MARS_...C260` besitzt dasselbe Endsuffix `C260`: sehr starker Identitätshinweis; vollständige lokale GATT-Identitätsprüfung weiterhin ausstehend.
- Ein zweiter Screenshot zeigt **`MZ_MZF002_0_A0A3B35EFDC8`**, offensichtlich die Ventilator-Seite. Er gehört **nicht** zur FC 3000 und ist kein Ziel dieses Arbeitsschritts.
- Die Screenshots beweisen weder die BLE-GATT-Characteristic-UUIDs der Lampe noch ihre Steuercodes. Die UUIDs des MZF002 nicht auf C260 übertragen.

**Nächster Schritt:** iPhone-seitigen HCI-Mitschnitt der nachweislich funktionierenden Mars-Legacy-Lichtsteuerung erfassen (Schreibvorgang mit physischem Effekt), dabei keine zweite aktive Verbindung zur FC 3000 versuchen.
