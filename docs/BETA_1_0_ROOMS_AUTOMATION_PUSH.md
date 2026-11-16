# Beta 1.0 – Räume, Benutzerrollen, Licht-/Luftautomation und Benachrichtigungen

Stand: 15.11.2026. **Umgesetzte Komponenten und offene Freigabeschritte ausdrücklich getrennt.**

## 1. Mehrere Benutzer pro Raum

Ein Raum/Zelt hat genau einen **Besitzer (Owner)**. Der Besitzer kann weitere Benutzer einladen; die Berechtigung wird stets **pro Raum**, nicht global am Raspberry Pi, vergeben. Ein eingeladener Benutzer kann Zugriff auf mehrere Räume bekommen, benötigt derzeit aber je Raum eine eigene Mitgliedschaft.

| Fähigkeit | Besitzer | Raum-Admin | Grower | Beobachter |
|---|---:|---:|---:|---:|
| Raum, Pflanzen, Messwerte ansehen | ✓ | ✓ | ✓ | ✓ |
| Growbuch lesen | ✓ | ✓ | ✓ | ✓ |
| Growbuch bearbeiten, Pflanzen pflegen | ✓ | ✓ | ✓ | – |
| Geräte betrachten, Kamera ansehen | ✓ | ✓ | ✓ | ✓ |
| Licht/Lüfter manuell bedienen | ✓ | ✓ | – | – |
| Automationen betrachten | ✓ | ✓ | ✓ | ✓ |
| Automationen bearbeiten/aktivieren | ✓ | ✓ | – | – |
| Grenzwertregeln verwalten | ✓ | ✓ | – | – |
| Alarmereignisse ansehen, Push selbst abonnieren | ✓ | ✓ | ✓ | ✓ |
| Einladungen erstellen | ✓ | eingeschränkt¹ | – | – |
| Mitglieder entfernen, Raum löschen | ✓ | – | – | – |

¹ Der Admin darf nur Grower/Beobachter einladen. Besitzübertragung ist nicht Teil der Beta. Für die erste Sicherheitsphase verwaltet ausschließlich der angemeldete Owner die bestehenden Mitgliedschaftsendpunkte.

**Einladungen:** Zeitlich begrenzte, einmalig verwendbare Token (SHA-256 im Speicher), per QR-Code, kopierbarem Link sowie als vom Benutzer selbst verschickbare SMS/E-Mail. Keine SMS-/Mail-Absendung über einen unkonfigurierten Dienst behaupten. Die eingeladene Person richtet eigenen Benutzernamen und Passwort ein. Ein Rollenwiderruf beendet bestehende Mitgliedersitzungen.

## 2. Licht- und Lüftungsautomation pro Raum

Die vorhandene `app/automation.py` verwaltet FRITZ!-Schaltsteckdosen. Sie ist **kein** Mars-Hydro-Licht-/Lüfterregler und darf nicht parallel mit BLE-Funktionen konkurrieren.

`app/room_control_plans.py` definiert derzeit sicher validierbare, **noch nicht scharf geschaltete** Pläne:

- Licht: Aus oder Zeitplan, Beginn/Ende auch über Mitternacht, Helligkeit 10–100 %, Mindestabstand zwischen Schaltvorgängen.
- Lüfter: Aus, feste Drehzahl oder Temperatur-/Feuchteschwelle, Grund- und Boost-Drehzahl, Hysterese, manuelle Halteposition oder Grunddrehzahl bei ungültigem Sensor.
- Jede Automatik ist raumgebunden, hat eine Vorschau und wird erst nach Hardware-Adapter, konkurrierenden Eingriffen, manueller Übersteuerung und Fail-Safe-Tests tatsächlich aktiviert.
- Immer protokollieren: Regel, aktueller/erwarteter Zustand, bestätigter Gerätewert und Herkunft (Benutzer, Automatik, Cloud).

## 3. Alarme und Push-Benachrichtigungen

`app/room_notifications.py` erzeugt raumgebundene Ereignisse anhand **echter, frischer Sensordaten**. Ohne gültige aktuelle Kalibrierung keine Bodenfeuchte-Grenzwertbehauptung. Konfigurierbar pro Raum:

| Ereignis | Bedingung | Standard |
|---|---|---|
| Temperatur unter/über Grenzwert | Messwert außerhalb des konfigurierten Bereichs über Mindestdauer | Keine ungefragten Grenzwerte |
| Luftfeuchte unter/über Grenzwert | Wie Temperatur | Keine ungefragten Grenzwerte |
| Bodenfeuchte unter/über Grenzwert | Gültiger kalibrierter Messwert | Keine ungefragten Grenzwerte |
| Boden-/Klimasensor offline oder veraltet | Kein frischer Wert nach konfigurierter Zeit | Separates Opt-in |
| Cloud-Fernkanal offline | Bestätigter Ausfall über Mindestdauer | Separates Opt-in |
| Licht/Lüfter offline | Gerät diesem Raum zugeordnet; Ausfall über Mindestdauer | **Standard aus**, abgesteckte Mars Hydro nicht als Fehler melden |
| Wiederherstellung | Nach tatsächlichem Rückkehr in gültigen Bereich bzw. Online | Einmalige Entwarnung |

**Schutz gegen Alarmflut:** Hysterese, Mindestdauer, ein Ereignis je Zustandswechsel, konfigurierbare Ruhezeiten (auch über Mitternacht). Eingestellte `cooldown_seconds` sind im Datenmodell vorhanden; vor Beta-Freigabe muss ihr Zusammenspiel mit wiederholten Ereignissen und Entwarnungen gesondert abgenommen werden.

## 4. Web Push: Technischer Stand und Freigabegates

In Git integriert:

- Raumbezogene Push-Subscription-API (`/api/v1/room-push`) mit Owner-/Mitgliedersitzung, Berechtigungsprüfung, Widerrufsschutz, begrenzten Registrierungen und ausgehender Endpoint-Allowlist.
- Speicherung der Push-Abonnements als geschützte Datei, keine Rückgabe von Endpunkt oder Schlüsseln über Status-API.
- Opt-in-basierte Übergabe neu erkannter Alarme an eine VAPID-/Web-Push-Sendeadapterfunktion; keine Zustellbehauptung bei fehlender Konfiguration.
- Gleiches Push-Anzeigeverhalten als Service-Worker-Code auf lokaler und Cloud-Seite.
- Ruhezeiten werden beim Versand berücksichtigt.
- `pywebpush>=2.5,<3` als Abhängigkeit vorgesehen.

**Noch nicht als iPhone-Push freigegeben:** Der aktuelle iPhone-Zugang ist `https://135ercloud.grow-central.de`. Seine persönliche Push-Subscription muss am selben HTTPS-Ursprung durch eine Benutzeraktion in der installierten Home-Screen-PWA erzeugt und über eine **Cloud-Account- und Raumrechte-verifizierende API** gespeichert werden. Die Cloud benötigt sichere VAPID-Konfiguration, Push-Worker-Registrierung, eigene Empfängerzuordnung und einen authentifizierten Eventtransport vom Pi. Ein lokaler `http://*.local`-Zugang alleine kann iOS-Home-Screen-Web-Push nicht bereitstellen.

Ein Push-Versand an den Push-Dienst ist auch noch **kein Zustell- oder Anzeige-Nachweis**. Beta-Abnahme erfordert einen echten iPhone-Test: Push-Berechtigung erteilen, Testschwelle auslösen, Sperrbildschirmmeldung erhalten, antippen, richtigen Raum öffnen, Ruhezeit und Widerruf prüfen, App schließen und erneut testen. Keine Push-Permission ohne expliziten Tap abfragen.

**Sicherheitsgrundsatz:** Ein eingeladener Benutzer darf seine eigenen Push-Geräte registrieren, aber keine fremden Subscriptions lesen oder manipulieren; nach Widerruf darf keine weitere Benachrichtigung an diese Person gehen. Keine Regeländerung oder Hardwaresteuerung über eine Push-Mitteilung selbst.

## 5. GUI-Parität und Beta-Freigabe

`.local` und `.de` behalten eine identische Final-Master-GUI. Zugang, Authentifizierung, WebSocket-Transport und origin-spezifische PWA-Service-Worker dürfen technisch abweichen, **Rechte, Menüs, Alarmregeln und Benachrichtigungseinstellungen nicht**. UI-Paritätstests sind vor jedem Cloud-Deployment Pflicht.

**Beta 1.0 ist erst freigabefähig**, wenn Einladungs-/Rollenberechtigungen auch im Cloud-Zugang tatsächlich greifen, Automation bei angeschlossenen Geräten verifiziert ist (oder klar als Vorschau ausgewiesen wird), Alarmzustände langfristig gespeichert werden, und iOS Push an ein abonniertes Gerät durchgehend nachweislich zugestellt werden kann.


## Cloud-Konten und sichere Gastverbindung (Entwicklungsstand 16.11.2026)

**Backend integriert:** Die produktive Cloud-API auf dem Plesk-Server hat jetzt zusätzlich die Account-gebundenen Endpunkte unter `/api/v2/collaboration`:

- Der authentifizierte Gerätebesitzer kann Einladungen für ein konkretes Gerät und eine Raum-ID mit Rolle `admin`, `grower` oder `observer` erzeugen. Der Token erscheint nur einmal als `/#room-invite=...` (URL-Fragment statt Server-Query), in der Datenbank liegt nur ein SHA-256-Digest.
- Ein bereits mit eigenem Cloud-Konto angemeldeter Empfänger kann den einmaligen Token über `POST /api/v2/collaboration/accept` einlösen.
- Mitgliedschaften sind an Geräte-ID, Raum-ID, eigenes Cloud-Konto **und das ursprüngliche Besitzerkonto** gebunden. Gerätewiderruf oder Besitzerwechsel entzieht die effektive Berechtigung. Besitzer können Rollen ändern und Mitglieder widerrufen.
- Kein Zugriff auf globale Gerätedaten durch Mitgliedschaft allein. Eine separate Gastverbindung darf erst später mit `get_membership_role()` **für jede Nachricht** und `GuestRequestBroker` für private Antwortzustellung eingebunden werden.

**Strikt noch deaktiviert:** Die bisherige `/api/v2/remote/connect`-Verbindung bleibt ausschließlich für das Cloud-Gerätebesitzerkonto zugelassen. Sie verteilt Antworten bisher geräteweit und darf **niemals** mit Gastkonten geöffnet werden, bevor Routing und Zugriffsschutz angepasst sind. Die künftige Gast-ACL in `cloud/v7/guest_remote_acl.py` ist getestet, aber noch nicht an den produktiven WebSocket angeschlossen. Sie erlaubt streng raumgebundene Leseabfragen und bestätigte Growbuch-Einträge für Grower/Admin, niemals Hardwaresteuerung oder kameraweiten Zugriff.

Die Cloud-PWA zeigt noch keinen fertigen Einladungsannahme-Assistenten; der in der API generierte `/#room-invite=...`-Link hat daher die explizite Kennzeichnung `acceptance_ui: pending`. Eine echte Einladung an eine andere Person und die Visualisierung beider PWA-Zugänge bleiben Abnahmen. `.local` und `.de` dürfen keine voneinander abweichenden Benutzeroberflächen bekommen.

**Prüfstand:** 33 isolierte Cloud-Konten-/WebSocket-ACL-/Integrationsprüfungen bestanden, produktive Cloud-API nach Restart gesund, WebSocket-Geräteverbindung wiederhergestellt, unauthentifizierter API-Zugriff auf Einladungserstellung HTTP 401. Die additive Cloud-Integration ist in `cloud/v7/room_membership.py` und `scripts/patch_cloud_room_membership.py` versioniert. Für einen Rollback wurde auf dem Cloud-Server eine Sicherung der vorherigen `app.py` angelegt. Bis zum Gast-WebSocket-End-to-End-Test bleibt Beta 1.0 **nicht freigegeben**.
