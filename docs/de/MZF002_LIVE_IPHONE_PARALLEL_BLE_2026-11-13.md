# MZF002: iPhone-Steuerung während paralleler Pi-BLE-Beobachtung (13.11.2026)

## Versuch
- iPhone Mars Legacy wurde zunächst vollständig geschlossen.
- Pi fand `MZ_MZF002_68756_A0A3B35EFDC8` wieder, stellte direkte BLE-Verbindung her und abonnierte GATT Notify `6f588463-f8f1-44f8-bdae-a1272a1b0f6e`.
- Pi sendete **keine BLE-Schreibbefehle**. Beobachtungszeit: 16:22:54–16:24:42 MEZ.
- Nutzer öffnete Mars Legacy und verstellte den Lüfter nach Aufforderung mit Zielstufen 25→50→75→100→25 %.
- Eine gleichzeitige passive WLAN-Paketaufzeichnung wurde bei diesem Versuch **nicht** vorgenommen. Daher ist der iPhone-zu-Gerät-Befehlsweg noch nicht direkt nachgewiesen.

## Verifizierte Notify-Statusänderungen

| Zeit (MEZ) | Sollwert % | RPM | Temperatur °C | Feuchte % |
|---|---:|---:|---:|---:|
| 16:22:56 | 25 | 800 | 18.3 | 54.1 |
| 16:23:35 | 50 | 800 | 18.4 | 54.0 |
| 16:23:41 | 50 | 2040 | 18.4 | 54.0 |
| 16:23:44 | 50 | 2060 | 18.4 | 54.0 |
| 16:23:53 | 76 | 2060 | 18.4 | 54.2 |
| 16:23:56 | 76 | 2640 | 18.3 | 53.9 |
| 16:24:05 | 100 | 2640 | 18.3 | 54.1 |
| 16:24:08 | 100 | 2940 | 18.4 | 54.0 |
| 16:24:11 | 100 | 2960 | 18.3 | 54.0 |
| 16:24:20 | 25 | 2940 | 18.3 | 54.0 |
| 16:24:23 | 25 | 1860 | 18.3 | 54.1 |
| 16:24:29 | 25 | 900 | 18.3 | 54.1 |
| 16:24:32 | 25 | 820 | 18.4 | 54.3 |
| 16:24:35 | 25 | 800 | 18.4 | 54.3 |

Alle Daten stammen aus der live laufenden Pi-BLE-Notify-Beobachtung, nicht aus simulierten Zuständen. Das Pi-Skript loggte nur Änderungen des auf Ein/Aus, Sollwert, RPM, Temperatur und Feuchte reduzierten Status. Vollständige Roh-BLE-Payloads wurden in diesem Durchlauf nicht gespeichert.

## Schlussfolgerung

**Nachgewiesen:** Pi und iPhone können während iPhone-Steuerung gleichzeitig zum MZF002 beitragen: iPhone änderte Sollwert, Pi erhielt über BLE Notifications den neuen Status. Die drei zeitlichen Stufenwechsel wurden vollständig erfasst. Die App erzeugte bei einem Zielwert von 75 % am Gerät den tatsächlichen Wert 76 %.

**Noch offen:** Die tatsächliche Übertragungsart des iPhone-Schreibbefehls (WLAN direkt, Cloud oder anderweitiger BLE-Kanal). Allein ein BLE-Notify vom Pi beweist nicht den Rückweg der iPhone-Steuerung. Für diesen Beweis ist eine eigene Aufzeichnung der WLAN-/BLE-Übertragung während eines Stufenwechsels nötig.

**Keine neue Steuerfunktion freigeschaltet.** Vermeide unbestätigte Schreibnutzlasten und sicherheitskritische Änderungen.
