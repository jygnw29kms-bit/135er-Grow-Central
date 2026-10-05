# TouranLive UI Master / Datenstrategie

Verbindlicher UI-Master ab 2026-10-05: **Master Bild 1 / OEM-Performance-Cluster**, fuer das Erisin-Radio in **1024x600 Landscape**.

Regeln:
- Immer Jens' roter VW Touran 1T3 (2012, CAVC) als Fahrzeugmotiv/Icons verwenden.
- Kennzeichen im UI-Master: B-JU 6969.
- VCDS/VAG ist die primaere Datenquelle; Standard-OBD/ELM327 bleibt Fallback.
- Keine Dummywerte. Nicht verfuegbare Werte werden als `—` dargestellt.
- Touch-Ziele und Schriftgroessen muessen fuer 1024x600 im Fahrzeug optimiert bleiben.
- VAG/OBD/Logger/DTC-Status muss jederzeit sichtbar sein.

## Log- und Adapteranalyse

TouranLive kann Logs und einen read-only Adapter-/Daten-Scan an `https://www.dezender.de/touran/api/upload-log.php` senden.
Der Scan prueft ohne Codierung/Schreibzugriffe:
- ELM-Adapteridentitaet, Protokoll, Spannung und OBD-Support-Bitmaps im OBD-Fallback,
- bekannte CAVC/MED17.5.5 VAG-Messwertbloecke im TP2.0/KWP2000-Modus,
- rohe Antworten fuer spaetere Analyse und Mapping.

Uploads erfolgen nur nach Nutzeraktion in der App (`LOG AN SERVER` oder `ADAPTER SCAN + SEND`).
Serverseitig werden Reports ausserhalb des Webroots unter `private/touran-logs` gespeichert.
