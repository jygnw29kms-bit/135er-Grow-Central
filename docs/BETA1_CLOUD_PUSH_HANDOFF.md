# Beta 1.0: Cloud-iPhone-Push, sicherer Auslieferungsplan

**Stand 18.11.2026: Code zur Registrierung/Widerruf auf Entwicklungsbranch, kein produktiver Versand, keine iPhone-Abnahme.** Diese Ergänzung gehört zum eingefrorenen privaten Einzelzelt-Umfang, nicht zu einer neuen Mehrzelt-Plattform.

## Architektur / Datengrenzen

- Raspberry Pi: unabhängige lokale Alarmerkennung und Growbuch-Archiv. Internetverlust darf weder die Steuerung noch die lokale Alarmerfassung unterbrechen.
- Cloud (HTTPS): Account-gebundene Web-Push-Abonnements mit Geräteprüfung, VAPID-öffentlichem Schlüssel und separatem Worker. Push-Geheimnisse verbleiben serverseitig. Kein Besitzer-Access-Token im Final-Master-iFrame oder Service Worker.
- Das iPhone muss die Cloud-PWA **auf dem Home-Bildschirm installiert** haben. Erst ein direkter Klick auf `Push aktivieren` fordert Berechtigungen an. Push-Abonnement `registered` ist **kein** Zustellungsnachweis.
- Cloud-API `GET/POST /api/v2/push/devices/{device_id}/status|subscriptions` und `DELETE /api/v2/push/devices/{device_id}/subscriptions/{id}` gehört nur einem authentifizierten Gerätebesitzer. Subscriptions sind individuell widerrufbar, HTTPS-Push-Service-URLs streng begrenzt, pro Gerät maximal fünf.
- Internes `submit_owner_alert` ist **kein HTTP-Endpunkt**. Vor einem Aufruf müssen Pi-Geräteidentität, Raumzuordnung, eventuelle Ruhezeiten sowie Opt-in/Push-Policy bereits durch einen separat gehärteten, authentifizierten Cloud-Relay-Handler geprüft sein. So lange diese Verbindung fehlt: kein Versand, Freigabegate BLOCKIERT.
- Accounts mit `status != active` und widerrufene Geräte werden bei jedem internen Versand ausgeschlossen. Keine Geheimnisse in HTTP-Antworten, Logs, Git, Nutzeroberfläche oder Diagnosetext.
- Im Fehlerfall keine automatische Wiederholung eines alarmierenden Ereignisses ohne Idempotenz-/Deduplikationsgarantie.

## Tatsächlicher Rootserver-Preflight (18.11.2026, nur lesend)

Plesk-Cloud-Dienste `135er-growcentral-cloud.service`, `135er-growcentral-cloud-admin.service` und `135er-growcentral-cloud-platform.service` waren **aktiv**. Die vorhandene Cloud-Kollaborations-API war eingebunden. Im verwendeten `/opt/135er-growcentral-cloud/venv/bin/python` waren **qrcode=False**, **pywebpush=False**; `/opt/135er-growcentral-cloud/cloud_push.py` war **nicht vorhanden**. Damit kann der Server derzeit weder den neuen Cloud-Push-Adapter laden, noch ist die QR-Laufzeitabhängigkeit für die bestehende Cloud-Einladungsfunktion nachgewiesen.

Für Folgeprüfungen gibt es jetzt `scripts/check_cloud_push_readiness.py`. Beispiel (nur boolesche Werte, keine Secrets):

```bash
python3 scripts/check_cloud_push_readiness.py \
  --backend /opt/135er-growcentral-cloud/app.py \
  --venv-python /opt/135er-growcentral-cloud/venv/bin/python \
  --push-worker /var/www/vhosts/EXAKTER-WEBROOT/gc-push-worker.js
```

Der letzte Webroot muss aus der tatsächlichen Cloud-Konfiguration ermittelt werden; `EXAKTER-WEBROOT` ist ausdrücklich **kein** bereits bestätigter Pfad. Exit 1 bedeutet: nicht freigabefähig. Installation/Update muss als atomarer, rücksetzbarer Vorgang erfolgen.

## Installationsabfolge (noch NICHT ausgeführt)

1. Aktuelle Cloud-Backend-Sicherung / Restorepunkt, bestehendes DB-Schema, Admin-/Owner-ACL und Service-Version erfassen. Für Cloud-System `cloud/v7/cloud_push.py` und das Werkzeug `scripts/patch_cloud_push.py` separat bereitstellen.
2. Testkopie des laufenden Cloud-Backends mit `patch_cloud_push.py --source <app.py> --output <neue-app.py>` erzeugen, Syntax und Abhängigkeiten prüfen. Originaldateien **nicht überschreiben**. Die Cloud-Web-Push-Python-Abhängigkeit `pywebpush` ist erst nach Review und Supply-Chain-Prüfung ins Ziel-Venv aufzunehmen.
3. `GC_CLOUD_VAPID_PUBLIC_KEY`, `GC_CLOUD_VAPID_PRIVATE_KEY` und `GC_CLOUD_WEBPUSH_SUBJECT` sicher als serverseitige Secrets einrichten. Niemals in Git, Logausgaben oder Client-JavaScript kopieren. `qrcode` und lokale Pi-Push-Secrets sind hiervon unabhängig.
4. Staging-Cloud-API: Owner-Status, Session-Ablauf, Widerruf, Invalid-Endpoint, bestehende Einladungen, Benutzerrollen und zweites Konto erneut prüfen. Keine Gäste auf Owner-Routen.
5. Cloud-Portal-Dateien inklusive root-scope `/gc-push-worker.js` atomar und cache-konsistent bereitstellen, nach Tests mit Rollbackmöglichkeit.
6. Sichere Pi-Event-Weitergabe nur über den authentifizierten, gerätegebundenen Cloud-Kanal; Raumidentität, Event-Deduplikation, Push-Policy, Ruhezeiten und Cloud-Gastberechtigungen explizit serverseitig durchsetzen.
7. Live-Abnahme mit installiertem iPhone-17-Pro-Max-PWA: Berechtigung, Abonnement, authentischer Grenzwertalarm, tatsächlicher Eingang, Klick öffnet korrekten Ursprung, Stummschaltung und sofortiger Widerruf. Fehler/Wartezeiten dokumentieren.
8. Erst nach erfolgreichen echten Tests `web_push` in `docs/BETA1_RELEASE_GATES.json` von `blocked` auf `verified` setzen und den manuellen Abnahmestand aktualisieren.

## Bewusst NICHT getan

Kein produktives Cloud-Schema geändert, keine VAPID-Schlüssel erzeugt/ausgelesen, keine Push-Subscription für den Betreiber angelegt, keine Nachricht ohne Einwilligung verschickt und keine bestehenden Gerätesitzungen geöffnet. Das aktuelle 135er-Branding bleibt unverändert.
