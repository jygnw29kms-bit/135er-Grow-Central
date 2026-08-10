# Smart Home

Die aktuelle Architektur bindet Shelly Gen2+ direkt lokal an. Tapo und FRITZ!SmartHome laufen über einen optionalen Home-Assistant-Connector. Apple Home und Siri werden über Home Assistant HomeKit Bridge erreicht. Matter ist das spätere standardsbasierte Bridge-Ziel.

Sicherheitsprinzip: kein entdecktes Gerät wird automatisch schreibbar. Freigabe, Schreibrecht, globaler Schalter und lokale Authentifizierung sind getrennte Hürden.
