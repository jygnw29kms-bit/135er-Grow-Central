# Grow-Central – Bereinigung und Validierung (15.11.2026)

## Ziel und Grenzen

Eine lokale Pi-PWA und eine Cloud-Zugangsoberfläche, keine zweite parallel gepflegte Cloud-GUI. Produktivdaten, Benutzerkonten, Messarchive und Kalibrierungen bleiben unangetastet. Mars-Hydro-Hardware ist laut Betreiber absichtlich nicht angeschlossen; Offline-Meldungen sind deshalb kein Hardwaredefekt.

## Erledigte Bereinigung

| Befund | Maßnahme | Prüfung |
|---|---|---|
| Alte Plesk-Startseite öffentlich | Außerhalb des Document-Roots mit Kopie und Prüfsumme archiviert | ursprüngliche URL HTTP 404 |
| Alte Cloud-Final-Master-HTML und alter Service Worker | Getrennt geschützt archiviert; aktuelle Cloud-Brücke bleibt erhalten | beide URLs HTTP 404; aktuelle Cloud HTTP 200 |
| Cloud-Manifest startete fälschlich auf `/ui` | Eigenes `cloud/portal/gc-manifest-cloud.webmanifest` mit Start `/` und Deployment-Änderung | Manifest öffentlich geprüft |
| Öffentlich ausgelagerte Pi-JavaScript-Altversion | Nach Sicherung aus `web/` entfernt | lokale API weiterhin erreichbar |
| Wiederholte Offline-BLE-Warnungen | Meldungen je Gerät/Fehlertyp gedrosselt, Wiederverbindung unverändert | acht BLE-Tests; Pi-Dienst mit Healthcheck neu geladen |
| USB- und BLE-Broker-Abfragen identisch | Gemeinsamer `broker_info_payload`-Handler in `app/provisioning/broker.py` | 27 Provisionierungstests; beide Routen verweigern unberechtigten Zugriff |
| Ungültiger systemd-Schlüssel am Pi-Mesh-Agent | `ConditionPathIsExecutable` durch gültiges `ConditionPathExists` ersetzt | `systemd-analyze verify` und Agent weiterhin aktiv |

## Bestandsanalyse

- Die erste vollständige Git-Inventur zeigte 755 identische Dateien, 114 fehlende und 22 abweichende Dateien. Viele fehlende Dateien gehörten zu nicht ausgelieferten CI-, Dokumentations- und alten Webbereichen.
- Ein gezielter Runtime-Vergleich zeigte 87 von 89 App-Dateien identisch. Die zwei Abweichungen betrafen ausschließlich Kommentare und wurden nach Sicherung mit Git angeglichen.
- Die nicht ausgelieferten alten Webmodule bleiben als Quellhistorie im Repository, zählen aber nicht mehr als fehlende aktive Runtime. Nur die freigegebenen `gc-final.*`-Dateien bilden die Pi-PWA.
- `SOURCE_COMMIT` und `BUILD` auf dem Pi bezeichnen weiterhin die ursprüngliche Betreiber-Image-Basis. Sie sind kein Beleg für den Stand nach einzelnen Dateiupdates und dürfen nicht künstlich umetikettiert werden.

## Automatische Kontrollen

- `scripts/verify_pi_installed_files.py --source-root <checkout> --runtime`: Python-App-Module, aktive PWA-Dateien und README gegen Git prüfen.
- `scripts/verify_cloud_final_master_deployment.py --source-root <checkout> --cloud-root <pfad>`: 17 Cloud-Dateien vergleichen, öffentlich verbliebene HTML-Backups und veraltete PWA-Dateien aufdecken.
- `scripts/verify_growcentral_readiness.py --mode all`: Pi-Dienste, API-Gesundheit, Zugriffsschutz, Cloud-HTTPS, PWA-Manifest und Alt-URLs prüfen; keine Steuerbefehle und keine Tokens.
- `grow-central-readiness-audit.timer`: stündliche, nicht privilegierte, lesende Prüfung. Ergänzt den bereits vorhandenen zweiminütigen Web-Watchdog, statt ihn zu ersetzen.

## Bestätigte Tests

- 47 Tests für Raumzuordnung, Messhistorie, Growereignisse, Fotos, Kamera, BLE und Final-Master/Audit erfolgreich.
- 27 Tests für Provisionierung und gemeinsamen Broker-Handler erfolgreich.
- 15 von 15 Prüfungen des kombinierten Pi-/Cloud-Readiness-Checks erfolgreich.
- Nach Cloud-PWA-Bereinigung: 17 von 17 aktuelle Cloud-Auslieferungsdateien identisch.
- Die Tests liefen auf dem Betreiber-Pi gegen dessen Python-Anwendungsabhängigkeiten und ein isoliertes temporäres `pytest`-Werkzeug. Die App-Umgebung wurde dafür nicht mit Testpaketen verändert.

## Weiterhin offen

- Authentifizierter End-to-End-Test der echten Raum-/Bodensensor-/Growbuchdaten. Ein automatisierter Versuch, lokale Zugangsdaten für diesen Test zu lesen, wurde durch eine Sicherheitskontrolle blockiert; diese Sperre wird nicht umgangen.
- Echte iPhone-PWA-Ansicht nach Anmeldung, Kamerabild und Gerätebedienung sind nicht vollständig abgenommen.
- Die historische Image-Version und die Git-Quellversion müssen im UI getrennt benannt werden; neue Versionsnummern erst nach dokumentierter Release-Abnahme.
- Alte Quellmodule nur nach nachgewiesener Referenzfreiheit und Testabdeckung aus Git entfernen. Die drei übrigen gefundenen gleichen Hilfsfunktionskörper bleiben wegen unterschiedlicher Modulverantwortung unverändert.

## Wiederherstellung

Alle in der Live-Installation entfernten Altdateien wurden vor dem Entfernen mit Prüfsumme bzw. Bytevergleich außerhalb des öffentlichen Webverzeichnisses gesichert. Der gewählte Pi-Python-Refactor hat getrennte Sicherungskopien unter `/var/backups/grow-central/`. Es wurden keine Datenbank-, Sensor-, Pflanzen- oder Nutzerdateien gelöscht.
