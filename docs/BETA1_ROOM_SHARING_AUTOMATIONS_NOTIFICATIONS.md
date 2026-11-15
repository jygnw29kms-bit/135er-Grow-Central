# Grow-Central Beta 1.0: Gemeinsame Räume, Automationen und Warnungen

Stand: 15.11.2026. Status: **Backend-Beta-Grundlage integriert**, noch **keine vollständige Freigabe** für externe Nutzer / Web-Push / automatische Hardwaresteuerung.

## Grundregeln

Ein physisches Zelt bzw. ein Raum hat genau einen Besitzer. Der Besitzer kann mehrere Mitglieder einladen, Rollen ändern und Zugriffe entziehen. Benutzerrechte gelten **pro Raum**, nicht global für den Pi. Die lokale Maschinen-API-Kennung darf niemals als Benutzerkonto oder Einladungsberechtigung wirken. Jede Berechtigungsprüfung erfolgt serverseitig.

### Rollenmatrix (Zielmodell)

| Funktion | Besitzer | Admin | Grower | Beobachter |
| --- | --- | --- | --- | --- |
| Raum und Livewerte anzeigen | ja | ja | ja | ja |
| Kamera ansehen | ja | ja | ja | ja |
| Growbuch lesen | ja | ja | ja | ja |
| Growbuch schreiben | ja | ja | ja | nein |
| Pflanzen bearbeiten | ja | ja | ja | nein |
| Geräte schalten | ja | ja | nein | nein |
| Geräte einem Raum zuordnen | ja | ja | nein | nein |
| Automationen ansehen | ja | ja | ja | ja |
| Automationen bearbeiten / aktivieren | ja | ja | nein | nein |
| Warnungen ansehen | ja | ja | ja | ja |
| Warnschwellen konfigurieren | ja | ja | nein | nein |
| Mitglieder einladen | ja | vorgesehen | nein | nein |
| Mitgliedsrechte ändern / entziehen | ja | nein | nein | nein |
| Besitzerrolle übertragen, Raum löschen | ja | nein | nein | nein |

**Wichtig:** Die Matrix definiert das beabsichtigte Berechtigungsmodell. Bisher sind nur ausdrücklich implementierte, raumbezogene Mitglieder-Endpunkte freigegeben. Insbesondere gibt es **keinen generischen Gast-Zugriff** auf vorhandene Admin-/Steuer-APIs. Hardwaresteuerung, Gerätezuordnung und Verwaltung der Automationen durch Mitglieder bleiben gesperrt, bis die gesonderte Berechtigungs- und Gerätetestabnahme abgeschlossen ist.

Implementiert in `app/room_permissions.py`, `app/room_sharing.py`, `app/room_members.py` und dem isolierten Authentifizierungspfad `app/auth_middleware.py`.

## Sichere Einladungen und Benutzer

- Der Hauptbesitzer erzeugt für einen vorhandenen Raum eine Einladung mit Rolle und begrenzter Lebensdauer (Standard 48 Stunden; maximal 7 Tage).
- Die API liefert Link, SVG-QR-Code und einmalig den geheimen Einladungstoken. QR-Code wird **lokal auf dem Pi** erzeugt und nicht an einen externen Dienst versendet.
- Link kann der Besitzer per iOS-Teilen-Funktion, SMS oder E-Mail selbst weitergeben. **Automatischer SMS-/E-Mail-Versand ist noch nicht angebunden.**
- Der Token wird nur als SHA-256-Prüfsumme gespeichert; im Freigabelink steht er als URL-Fragment, damit der Webserver ihn nicht als Query-Parameter erhält.
- Annahme nur einmalig, vor Ablauf, für einen existierenden Raum und mit eigenem Benutzernamen sowie mindestens 12 Zeichen langem Passwort. Passwort nur als PBKDF2-Verifizierer gespeichert.
- Mitglieder erhalten eine gesonderte HttpOnly-Sitzung. Die Sitzung kann ausschließlich `/api/v1/room-members/` verwenden; bestehende Besitzer- und Maschinen-APIs bleiben gesperrt.
- Einladungen können widerrufen, Mitglieder deaktiviert und Rollen geändert werden. Beim Widerruf werden gespeicherte Mitgliedssitzungen gelöscht.
- Das lokale `/join` bietet die Anmeldung/Einladungseinlösung und eine schmale Ansicht des freigegebenen Raums.

Derzeitig **nur lokaler Zugangsweg**: Die Standard-Linkadresse ist `http://135er-grow-central.local/join#invite=...`. Für Einladungen und Rollen über `.de` fehlt noch die Zuordnung zu den bestehenden Cloudkonten und zur autorisierten Gerätefreigabe. Diese Arbeit ist Pflicht vor einer **externen** Beta-Einladung. Der Einladungslink allein erteilt keine unbeschränkten Geräte- oder Cloudrechte.

### Besitzer-API (lokale Sitzung erforderlich)

`GET /api/v1/room-sharing/policy`: Rollen und Berechtigungen.

`POST /api/v1/room-sharing/{room_id}/invitations`: Einladung mit `role`, `delivery_hint`, `ttl_hours`; Antwort enthält QR-SVG und Link einmalig.

`GET /api/v1/room-sharing/{room_id}/invitations`: Metadaten ohne Geheimtoken.

`DELETE /api/v1/room-sharing/{room_id}/invitations/{invitation_id}`: Einladung widerrufen.

`GET /api/v1/room-members/owner/{room_id}/members`, `PATCH /api/v1/room-members/owner/{room_id}/members/{member_id}`, `DELETE /api/v1/room-members/owner/{room_id}/members/{member_id}`: Mitglieder sehen, Rolle wechseln, Zugang entziehen.

### Mitglieder-API

`POST /api/v1/room-members/accept`, `POST /api/v1/room-members/login`, `POST /api/v1/room-members/logout`, `GET /api/v1/room-members/status`.

Nur für zugewiesene Räume und erlaubte Aktionen: `GET /api/v1/room-members/room/{room_id}`, `GET/POST /api/v1/room-members/room/{room_id}/journal`, `GET /api/v1/room-members/room/{room_id}/alerts`, `GET /api/v1/room-members/room/{room_id}/automation`.

## Licht- und Lüftungsautomation pro Raum

Implementiert: `app/room_control_plans.py` und lokale Besitzer-API `/api/v1/room-control-plans/{room_id}` (GET/PUT) sowie `/preview` (POST).

- **Licht:** Aus / Zeitplan, inklusive über Mitternacht laufender Hell-/Dunkelzeiten, Helligkeit und Mindestzeit zwischen zwei Schaltvorgängen.
- **Lüfter:** Aus / konstante Stufe / temperaturabhängig / luftfeuchteabhängig. Basis- und Boost-Stufen, Hysterese, Mindestumschaltzeit.
- **Sensorfehler:** Ungültige, fehlende und veraltete Messwerte dürfen keine neue Boost-Regel auslösen. Konfigurierbare Strategie `manual_hold` oder `base_speed`.
- **Manuelle Eingriffe:** Später mit zeitlich begrenztem Vorrang (Override) und protokollierter Rückkehr zum Automatikmodus.
- **Wiederanlauf:** Nie blind volle Leistung schalten, bevor Soll-/Istzustand und tatsächliches Gerät verifiziert sind.
- **Keine parallele Regelengine:** Die vorhandene FRITZ!-Automation bleibt erhalten. Die raumbezogenen Pläne benutzen später die gemeinsamen Geräteadapter und einen abgestimmten Scheduler.

**Aktuelle Grenze:** `execution=simulation_only_not_armed`. Auch wenn `enabled=true` in einem gespeicherten Plan steht, erzeugen diese Endpunkte **keine physischen Schaltbefehle**. Erst bei vorhandener Hardware und bestätigten Aktor-, Timeout-, Override- und Sicherheitsprüfungen aktivieren.

## Warnungen und Push

Implementiert: `app/room_notifications.py` und lokale Besitzer-API `/api/v1/room-notifications/{room_id}` (GET/PUT).

- Pro Raum einstellbare Grenzen für Temperatur, relative Luftfeuchte und Bodenfeuchte.
- Unterschreitungen, Überschreitungen und Entwarnung als separate Ereignisse.
- Mindestdauer vor Auslösung, Hysterese und persistente Zustände verhindern Alarmflattern.
- Eigenständige Sensor-Offline-Warnung, wahlweise aktiv.
- Cloud-Verbindungsstörungen erst nach definierter Ausfalldauer und nur bei ausdrücklichem Opt-in. Mars-Hydro-Lampe und -Lüfter werden bei Opt-in einzeln nur dann geprüft, wenn das jeweilige Gerät dem Raum zugewiesen ist.
- Absichtlich getrennte Mars-Hydro-Geräte lösen standardmäßig **keinen** Störungsalarm aus.
- Ereignisse in einem lokalen, raumgebundenen Postfach; eine Minute Prüfintervall; Warnungsstatus nur für berechtigte Benutzer sichtbar.

**Push auf iPhone:** Noch **nicht zugestellt**. Erforderlich sind ein HTTPS-Cloud-PWA-Service-Worker, VAPID-Schlüssel, sichere geräte-/kontogebundene Push-Abonnements, iOS-Mitteilungsfreigabe durch eine aktive Benutzerhandlung, ein Cloud-Relay für die lokalen Warnereignisse und ein bestätigter Zustellungstest. Die Push-Subscription-URL ist geheim zu halten und mit der Benutzeridentität zu verbinden. Siehe [Apple Web Push](https://developer.apple.com/de/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers) und [MDN Push API](https://developer.mozilla.org/de/docs/Web/API/Push_API).

Push muss den Zustand `ausgelöst / zugestellt / fehlgeschlagen / bestätigt / entwarnt` unterscheidbar protokollieren. Ruhezeiten dürfen echte kritische Sicherheitswarnungen nicht unsichtbar machen. Bei wiederhergestellter Verbindung kommt höchstens eine konsolidierte Entwarnung, kein Schwall historischer Pushs.

## Beta-Abnahme und offene Punkte

1. Lokaler Besitzer erstellt und widerruft Einladung; QR und Link werden gegen eine echte zweite iPhone-/Browser-Sitzung geprüft.
2. Ein eingeladener Grower kann nur seine zugewiesenen Räume und erlaubten Journale sehen; Gastzugriff auf Geräteadministration und andere Räume wird aktiv verweigert.
3. Cloud-Konten und Rollen werden sicher auf **denselben Besitzer, dieselben Räume und Berechtigungen** abgebildet. `.local` und `.de` behalten stets die gleiche Final-Master-Oberfläche.
4. Bedienoberfläche für Mitgliederverwaltung, Einladungslink, QR, Rollen und Automationseditor **gemeinsam** für Pi und Cloud gestalten und synchron ausrollen. Der derzeitige lokale `/join` ist ein separater, bewusst reduzierter Onboarding-Screen, **nicht** die vollständige Final-Master-GUI.
5. Erst nach Hardwaretest Licht-/Lüftungsregeln scharf schalten. Testfälle Zeitumstellung, Stromausfall, nicht erreichbarer Sensor, HomeKit-/BLE-Konflikte und manuelles Override.
6. VAPID/Push-Abos auf Cloud-PWA einrichten, Opt-in mit iPhone-Home-Screen-PWA testen, Meldung und Entwarnung wirklich empfangen.
7. Login-Ratelimit, CSRF-Strategie und Einladungs-/Mitgliederdaten in Backup/Restore integrieren; DSGVO-konforme Aufbewahrungs- und Löschregeln sowie Einwilligungs- und Versandprotokolle dokumentieren.
8. Sicherheitsabnahme und vollautomatische Tests vor Beta-Tag.

## Bisherige technische Nachweise

- 44 Tests bestanden: Rollen, QR-Erzeugung, Einladungseinlösung, abgelaufene und widerrufene Links, Gast-API-Isolation, tatsächlicher HTTP-Ablauf bis zum Entzug, Lichtzeitpläne, Lüfterhysterese, Sensorwarnungen, Cloud-Offline-/Entwarnungslogik sowie bestehende Raum- und Automationsfälle.
- Neue Backend-Module auf dem Grow-Pi installiert. Lokaler Gesundheitsendpunkt HTTP 200, HomeKit/Provisionierung/Remote-Kanal weiter aktiv.
- Kein vorhandenes Sensor-, Pflanzen-, Kamera-, Foto- oder Growbuchdatum wurde überschrieben.
- **Kein Beta-Freigabevermerk für die Gesamtfunktion.** Cloud-Mitgliederfreigabe, Pushzustellung und Hardwareautomatik bleiben ausdrücklich unvollständig.
