# Sensoren und Historie

## Sensor Registry

Jeder Sensor erhält mindestens ID, Site, Typ, Einheit, Quelle, Status und Kalibrierungsinformationen.

Typische Werte:

- Temperatur
- relative Luftfeuchtigkeit
- VPD
- Taupunkt
- Geräte-RPM/Leistung
- Systemwerte des Raspberry Pi

## Historie

Messwerte werden mit Zeitstempel gespeichert. Das Dashboard zeigt aktuelle Werte und Zeitreihen. Die lokale Historie kann begrenzt sein, während die Cloud längere Retention bereitstellt.

## Datenqualität

- Plausibilitätsgrenzen
- Kennzeichnung fehlender Werte
- Timestamp-Validierung
- optionales Glätten nur für Darstellung, Rohwert bleibt erhalten
- Sensor-Offline-Erkennung per Heartbeat/Timeout
