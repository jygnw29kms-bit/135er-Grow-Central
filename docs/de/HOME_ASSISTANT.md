# Grow Central mit Home Assistant, Apple Home, Alexa und Google

Grow Central bleibt die Geräte- und Sicherheitsverwaltung. Die lokale Integration
exportiert ausgewählte, freigegebene Messwerte und Schalter nach Home Assistant.
Apple Home/Siri, Google Assistant und Alexa werden über die von Home Assistant
gepflegten Integrationen angebunden. Android und iOS können außerdem die
Home-Assistant-Companion-App für Anzeige und Bedienung verwenden.

## 1. Grow Central konfigurieren

Nach dem First-Boot-Setup einen separaten zufälligen Brücken-Zugangsschlüssel mit
mindestens 32 Zeichen erzeugen, beispielsweise mit `openssl rand -hex 32`. Nur in
die lokale geschützte Konfiguration übernehmen; nicht in Git oder Chat einfügen.
Dieser Schlüssel gewährt ausschließlich Zugriff auf den Home-Assistant-Export,
keinen administrativen Zugriff auf Grow Central.

In der bestehenden Grow-Central-Umgebungsdatei setzen und den Dienst neu starten:

```dotenv
GC_HA_EXPORT_ENABLED=true
GC_HA_BRIDGE_TOKEN=<eigener-zufaelliger-schluessel>
GC_HA_EXPORT_DEVICE_IDS=lamp,growcentral_esp32:gc-soil-aabbcc
GC_HA_EXPORT_SWITCH_IDS=lamp
```

Die IDs durch die tatsächlich registrierten Geräte ersetzen. Weitere konfigurierte
Runtime-Sensoren, beispielsweise `zigbee:climate` oder `mqtt:climate`, können
ausdrücklich als Messwerte ausgewählt werden; sie erhalten keine Schaltrechte. Leere Listen
exportieren nichts. Native Sensoren müssen vorher manuell angenommen sein.
Schalter benötigen zusätzlich `approved=true`, `writable=true` und
`GC_SMARTHOME_ENABLED=true`. Von Home Assistant importierte Geräte werden nicht
zurückexportiert. Die Freigaben werden bei jedem Schaltbefehl erneut geprüft;
Widerruf macht die entsprechende HA-Entität beim nächsten Polling unverfügbar.

API: `GET /api/v1/home-assistant/snapshot` und
`POST /api/v1/home-assistant/devices/{id}/switch` mit JSON `{"on":true}` und
`Authorization: Bearer <Brückenschlüssel>`. Der Export enthält keine privaten
Schlüssel, Netzwerkpasswörter, Rohmetadaten oder Pflanzenjournale.

Home Assistant muss Grow Central im lokalen Netzwerk erreichen. HTTPS mit einem
von Home Assistant vertrauten Zertifikat verwenden. HTTP ist nur für ein
vertrauenswürdiges, isoliertes lokales Netz vorgesehen; es verschlüsselt den
Zugangsschlüssel nicht. TLS-Prüfung ist aktiviert, Weiterleitungen sind gesperrt.
Keine Router-Portfreigabe für die Grow-Central-API einrichten.

## 2. Integration installieren

Den Ordner `integrations/home_assistant/custom_components/grow_central` aus diesem
Repository nach `/config/custom_components/grow_central` der
Home-Assistant-Installation kopieren. Bei Home Assistant Container den Ordner im
eingebundenen Konfigurationsverzeichnis verwenden. Danach Home Assistant neu
starten und unter **Einstellungen → Geräte & Dienste → Integration hinzufügen →
Grow Central** die lokale URL (z. B. `https://growcentral.example`) und den
Brückenschlüssel eintragen. Keine Pfade oder Zugangsdaten in die URL schreiben.

Die Integration fragt alle 30 Sekunden ab, ergänzt neu freigegebene Entitäten,
meldet Offline-Geräte als unverfügbar und liest Schaltzustände nach Befehlen
zurück. Zugangsfehler lösen eine erneute Authentifizierung aus. Bei URL-Wechsel
die Integration entfernen und mit der neuen URL hinzufügen. Unterstützt werden
Bodenfeuchte, Temperatur, Luftfeuchte und verfügbare elektrische Messwerte.
Nicht jeder Gerätetyp liefert alle Werte. Energiemesswerte werden nicht pauschal
als monotoner Gesamtzähler markiert.

## 3. Apple Home und Siri

In Home Assistant **HomeKit Bridge** hinzufügen und ausschließlich die gewünschten
Grow-Central-Entitäten auswählen. Alternativ das Beispiel
`integrations/home_assistant/examples/homekit.yaml` mit echten Entitäts-IDs in die
HA-Konfiguration übernehmen. Die Bridge anschließend mit ihrem angezeigten
Kopplungscode in der Apple-Home-App hinzufügen. Siri nutzt die dort vergebenen
Gerätenamen. iPhone und Bridge müssen sich für die Kopplung im erreichbaren
lokalen Netz befinden; mDNS darf nicht durch eine Netztrennung blockiert sein.
Für Apple-Fernzugriff eine unterstützte Apple-Steuerzentrale verwenden.

HomeKit unterstützt unter anderem Temperatur und Luftfeuchte, aber keinen
numerischen Bodenfeuchtesensor mit der HA-Klasse `moisture`. Bodenfeuchte bleibt
im Home-Assistant-Dashboard verfügbar; sie wird nicht fälschlich als Luftfeuchte
ausgegeben. Auch Google Assistant unterstützt numerische `moisture`-Sensoren
derzeit nicht. Die Anzeige und Siri-Abfrage unterstützter Messgrößen müssen am
echten Telefon geprüft werden. Grow Central selbst ist kein zertifiziertes
HomeKit- oder Matter-Gerät.

## 4. Alexa und Google Assistant

Der einfachste gepflegte Weg ist **Home Assistant Cloud (Nabu Casa)**:
In Home Assistant anmelden, Alexa beziehungsweise Google Assistant aktivieren,
gewünschte Entitäten ausdrücklich freigeben und das entsprechende Konto in der
Alexa- beziehungsweise Google-Home-App verknüpfen. Der Cloud-Dienst benötigt ein
Konto und gegebenenfalls ein kostenpflichtiges Abonnement. Nur benötigte
Schalter freigeben; Sensorabfragen hängen von den Fähigkeiten des jeweiligen
Assistenten ab. Google Home und Alexa auf Android verwenden diese gleichen
Konto-Verknüpfungen. Die Companion-App benötigt keine Sprachassistenten-Brücke.

Alternativ bieten die offiziellen HA-Integrationen eine manuelle Einrichtung:
Google erfordert ein eigenes Projekt und Account Linking; Alexa eine eigene
Smart-Home-Skill und die dazugehörige Backend-/Account-Linking-Konfiguration.
Diese externen Konten, Client-Geheimnisse und Freigaben können nicht im Repository
für den Nutzer angelegt werden. Dafür ausschließlich die offiziellen Anleitungen
verwenden. Kein universeller Sprachsteuerungs-Endpunkt wird nach außen geöffnet.

## Prüfung und Grenzen

Die Integration wurde mit Home Assistant 2025.1.4 (Python 3.12) und 2026.10.1
(Python 3.14) geprüft. Softwaretests prüfen Zugriffstrennung, Auswahl, Schaltfreigaben, Widerruf,
Offline-Zustände, Polling und Home-Assistant-Entitäten. Die Kopplung mit einem
echten iPhone/Android-Gerät, Apple-Steuerzentrale, Echo oder Google-Lautsprecher
und die Geräteschaltung sind separat auf der Zielinstallation zu prüfen.

BLE-Sensor-Provisionierung gehört zum Sensor-Onboarding und wird durch diese
Integration nicht ersetzt. Zertifikate und individuelle MQTT-Zugänge der Sensoren
müssen entsprechend `SENSOR_PAIRING.md` eingerichtet sein.

## Offizielle Quellen

- HomeKit Bridge: https://www.home-assistant.io/integrations/homekit/
- Google Assistant: https://www.home-assistant.io/integrations/google_assistant/
- Alexa: https://www.home-assistant.io/integrations/alexa/
- Home Assistant Cloud: https://www.home-assistant.io/integrations/cloud/
- Companion Apps: https://companion.home-assistant.io/

Die HA-Webseiten antworteten beim direkten Abruf mit HTTP 403. Ihre offiziellen
Quelldokumente im Repository `home-assistant/home-assistant.io` (Branch `current`,
`source/_integrations/{homekit,google_assistant,alexa,cloud}.markdown`) wurden am
13.10.2026 erfolgreich abgerufen und für die beschriebenen Einrichtungswege und
Sensorklassen geprüft. Die Konto-Kopplung bleibt auf der Zielinstallation zu
verifizieren.

## Native Sensoren vorbereiten

Das neue USB-Test-Image kann den XIAO-C3-Sensor direkt in GC flashen und dessen
individuellen MQTT-TLS-Zugang einrichten. Danach Name/Raum zuweisen, bevor die
Sensor-ID in die HA-Exportliste aufgenommen wird:
[USB-Sensor einrichten](USB_SENSOR_SETUP.md).
