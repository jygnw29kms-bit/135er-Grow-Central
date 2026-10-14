# App-Analyse und Quellenabgleich · 9. Oktober 2026

## Umfang und Ergebnis

Geprüft wurden die lokale Python-App, ihre Desktop-/Mobile-Laufzeitanzeigen, die Cloud-API, Cloud-Link V2, vorhandene Tests, Roadmap und Quellenregister. Änderungen betreffen den gemeinsamen Cloud-Status und die Wiederverbindung. Projektfremde Anwendungen wurden nicht verändert. Dies ist keine vollständige Prüfung aller Geräteprotokolle oder ein Hardware-Freigabenachweis.

**Implemented:** Ein persistiertes `connected` genügt nicht mehr für einen aktuellen Verbindungsstatus. Ein fehlender, ungültiger, deutlich zukünftiger oder abgelaufener Zeitstempel und ein geänderter Server führen zu `stale`. Das Zeitfenster berücksichtigt das konfigurierte Sync-Intervall sowie Diagnose- und Upload-Laufzeiten. Die Status-API liefert zusätzlich `state`, `stale`, `updated_at` und `age_seconds`; die Laufzeit-API übernimmt diese Informationen für Desktop/Mobile. Deaktivierte Cloud wird immer als deaktiviert angezeigt. Stale Cloud erzeugt einen Hinweis und blockiert den lokalen Betrieb nicht.

**Implemented:** Die systemd-Prüfung läuft über `asyncio.to_thread`; ein fehlendes Programm oder Timeout liefert einen inaktiven Dienst statt HTTP 500. Die Health-Prüfung bestätigt die Grow-Central-Serviceidentität und bleibt gegenüber dem Agent-Heartbeat nur beratend.

**Implemented:** Status-Probe und Agent teilen eine HTTPS-Origin-Prüfung. Eingebettete Zugangsdaten, Query, Fragment, Pfad, ungültige Ports und Leer-/Steuerzeichen werden abgelehnt. Ein ungültiger Ursprung wird nicht abgefragt oder als URL zurückgegeben. Dies ist URL-Validierung, keine DNS-basierte SSRF-Sperre; selbst gehostete HTTPS-Server bleiben möglich.

**Implemented:** Nach inkompatibler Cloud-Health-Antwort oder HTTP 404 des Telemetrie-Endpunkts setzt V2 seinen Verbindungszustand zurück. Bei erfolgreicher Wiederverbindung erfolgt erneut der Diagnose-Handshake.

## Verifizierte Primärquellen

Die Originaldokumentation wurde am 9. Oktober 2026 über die offiziellen GitHub-Repositories abgerufen. Direkter Zugriff auf die Dokumentationsdomains war durch die Netzwerkregeln gesperrt. Der Bezug ist durch feste Quellstände nachvollziehbar:

| Quelle | Verifizierte Aussage | Umsetzung / Bewertung |
|---|---|---|
| [CPython 3.12: asyncio](https://github.com/python/cpython/blob/58ed60b7415e218ce3d608302e39b5e55bfb0e88/Doc/library/asyncio-task.rst), Abschnitt „Running in Threads“ | Blockierende I/O in einer Coroutine blockiert den Event Loop; `to_thread` lagert sie aus. | Bisher fehlende Berücksichtigung bei der Cloud-Dienstprüfung korrigiert. |
| [CPython 3.12: urllib.parse](https://github.com/python/cpython/blob/58ed60b7415e218ce3d608302e39b5e55bfb0e88/Doc/library/urllib.parse.rst), „URL parsing security“ | `urlparse` und `urlsplit` validieren Eingaben nicht; sicherheitsrelevante Komponenten müssen separat geprüft werden. | Reine HTTPS-Origin-Prüfung ergänzt; Parserfehler werden behandelt. |
| [HTTPX: Async Support](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/docs/async.md), „Opening and closing clients“ | Wiederholtes Erzeugen von Clients in häufigen Schleifen verhindert effizientes Connection Pooling. | V2 verwendet bereits einen Client für seine Schleife. Ein langlebiger Client für Statusanfragen bleibt eine mögliche weitere Optimierung und benötigt einen sauber verwalteten App-Lebenszyklus. |
| [Kanonischer Release-Status](../../RELEASE_STATE.md) | Build 351 ist Candidate; Hardwarevalidierung ist offen. | Veraltete Build-118-Angabe in der Roadmap korrigiert. |

Diese Quellen liefern belastbare Softwarehinweise, aber keine neuen bestätigten Mars-Hydro-BLE-Kommandos. Die in [SOURCES](../SOURCES.md) und [SMART_HOME_SOURCES](../SMART_HOME_SOURCES.md) aufgeführten Herstellerinformationen wurden in dieser Änderung nicht erneut live geprüft. Aus ihnen wurde keine neue Hardwarefreigabe abgeleitet.

## Prüfungen und Grenzen

- Python-Regressionstests einschließlich Statusalter, Serverwechsel, URL-Fehlern, fehlendem systemd und nicht blockierender Dienstprüfung.
- Wiederverbindungsablauf mit simuliertem Health-Ausfall und Telemetrie-404; danach wird `reconnect` bestätigt.
- Laufzeit-API: veraltete Cloud erzeugt einen Hinweis bei weiter funktionsfähigem lokalen Core.
- Stand nach der Änderung: 241 Python-Tests bestanden; bestehende Deprecation-Warnungen bleiben sichtbar.

**Experimental / offen:** Reale BLE/GPIO/Kamera- und Provider-Validierung, Langzeitmessungen auf Pi 3/4/5, mobile Realgeräte, produktive Cloud-Verbindungen und neue Image-Builds wurden nicht geprüft. Ein frischer persistierter Heartbeat ist keine kontinuierliche Erreichbarkeitsgarantie. Host und Pi benötigen eine verlässliche Uhr. Im V2-Agent ist kein Remote-Command-Polling implementiert; seine Remote-Command-Konfiguration ist deshalb kein Nachweis einer funktionsfähigen Fernsteuerung. Automationen speichern derzeit Definitionen; daraus folgt kein Nachweis eines laufenden Zeit-/Temperatur-Regelmotors.
