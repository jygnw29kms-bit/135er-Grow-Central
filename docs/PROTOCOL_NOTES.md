# DF100M / MZF002 – Testnotizen

Früher Teststand auf Basis der bisher gefundenen Mars-Legacy-Daten.

## Kandidaten

Service:
`6f588463-f8f1-44f8-bdae-a1272a1b0f6e`

Characteristics:
`83677baa-3eb8-4866-b6b6-96e5ed5cc48d`
`f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d`

App-Strings:
`MZ_MZF`
`wind_set_speed`
`wind_speed`
`wind_speed_num`
`RPM`

## Testmatrix

| Test | Write UUID | Payload | Erwartung |
|---|---|---|---|
| A | f5d2... | 0A | 10 % oder Reaktion |
| B | f5d2... | 14 | 20 % oder Reaktion |
| C | f5d2... | 32 | 50 % oder Reaktion |
| D | 8367... | 0A | nur falls Write-Property vorhanden |

Wenn keine Reaktion erfolgt, zuerst `/api/services` prüfen. Nur Characteristics mit `write` oder `write-without-response` verwenden.
