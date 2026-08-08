# Troubleshooting

## DF100M wird nicht gefunden

- Mars Legacy vollständig beenden.
- Bluetooth am Raspberry Pi prüfen.
- Abstand zum Gerät reduzieren.
- `bluetoothctl scan on` testen.
- prüfen, ob ein anderes Telefon bereits verbunden ist.

## Verbindung schlägt fehl

```bash
sudo systemctl restart bluetooth
```

Danach erneut testen.

## GATT liefert keine erwarteten UUIDs

Das ist wertvolle Information. Die aktuell dokumentierten UUIDs sind Kandidaten aus der Analyse, keine garantierte Zuordnung.

Ausgabe sichern und mit `docs/DF100M_PROTOCOL.md` vergleichen.

## Speed-Test funktioniert nicht

Zu erwarten, solange das echte Payload-Format noch nicht bestätigt ist.

Keine zufälligen langen Binärsequenzen senden. Stattdessen Legacy-Traffic erfassen und reproduzieren.

## Webinterface nicht erreichbar

```bash
ss -ltnp | grep 8080
```

und:

```bash
curl http://127.0.0.1:8080/api/health
```
