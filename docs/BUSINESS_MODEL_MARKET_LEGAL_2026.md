# Grow-Central Geschäfts-, Markt- und Rechtsmodell

Stand: 2026-10-17

> Arbeits- und Entscheidungsgrundlage, keine individuelle Rechtsberatung. Vor einem öffentlichen Bezahlstart müssen AGB, Datenschutzerklärung, Widerruf/Kündigung, Haftungsklauseln und Produkt-/Hardwarepflichten durch eine in Deutschland zugelassene Rechtsberatung geprüft werden.

## 1. Strategische Grundentscheidung

Grow-Central bleibt **local-first und Open Source im Kern**. Monetarisiert werden nicht grundlegende lokale Funktionen, sondern zusätzliche Leistungen mit realem laufendem Aufwand oder erkennbarem Mehrwert:

1. optionaler Remote-/Cloud-Link,
2. Offsite-Backups und Wiederherstellung,
3. Langzeithistorie und erweiterte Auswertungen,
4. Mehrbenutzer- und Multi-Site-Funktionen,
5. Support / Komfortleistungen,
6. optionaler Vertrieb handelsüblicher Raspberry-Pi- und Sensor-Komponenten als DIY-Zusammenstellung mit Dokumentation.

Keine künstliche Beschneidung der lokalen Software, kein Cloud-Zwang, keine kostenpflichtige Freischaltung grundlegender Gerätesteuerung.

## 2. Positionierung

### Kernversprechen

**Grow-Central ist eine lokale, offene Steuerungsplattform für Indoor-Grow- und Pflanzenumgebungen, die auch ohne Cloud vollständig weiterläuft.**

Der Bezahlservice verbindet eine bestehende lokale Installation sicher mit Remotezugriff, Backups, Push-Benachrichtigungen und Langzeitdaten.

### Abgrenzung

- gegenüber Hersteller-Apps: herstellerunabhängig, lokal, offene Schnittstellen;
- gegenüber reinen Monitoren: Automationen, Geräteintegration und zentrale Steuerung;
- gegenüber Home Assistant: deutlich engerer Pflanzen-/Grow-Fokus und geführte Bedienung;
- gegenüber professionellen Gewächshaus-/Cannabiscontrollern: deutlich günstiger, DIY-freundlich und für kleine Setups geeignet.

## 3. Zielgruppen

### A. Technikaffine Homegrower / Indoor-Gärtner

Wichtigste Startzielgruppe. Erwartet niedrigen Preis, Datenschutz, einfache Einrichtung und zuverlässige lokale Funktion.

### B. Enthusiasten mit mehreren Räumen/Zelten

Höhere Zahlungsbereitschaft für Historie, mehrere Geräte, Push, Reports und Fernzugriff.

### C. Kleine Vereine / legale Gemeinschaftsprojekte / nicht-gewerbliche Setups

Nur anbieten, soweit der konkrete Einsatz rechtlich zulässig ist. Interessant für Mehrbenutzerrechte, Audit und mehrere Räume. Kein Marketing, das den Konsum oder die Weitergabe von Cannabis bewirbt.

### D. Allgemeine Indoor-Horticulture

Strategisch wichtig, um Grow-Central nicht rechtlich und wirtschaftlich ausschließlich an Cannabis zu binden: Chili, Tomaten, Kräuter, Jungpflanzen, Orchideen, Pilz-/Terrarien-nahe Klimasteuerung soweit technisch passend.

## 4. Produkt- und Preisstruktur

### Grow-Central Core — kostenlos

- lokale PWA / Weboberfläche
- lokale Geräte- und Sensorverwaltung
- lokale Automationen
- lokale Historie in sinnvoller Grundtiefe
- Home-Assistant-/Smart-Home-Anbindung
- lokale API
- Backup/Export lokal
- Open-Source-Code

Ziel: Vertrauen, Community, Verbreitung und Hardwareunabhängigkeit.

### GC Link — empfohlen 5,99 EUR/Monat oder 59 EUR/Jahr inkl. USt. im B2C-EU-Modell

- sicherer Remotezugriff ohne eingehende Portfreigabe
- Push-/E-Mail-Benachrichtigungen außerhalb des Heimnetzes
- Cloud-Status und Offline-Erkennung des Pis
- verschlüsseltes Offsite-Backup
- geführte Wiederherstellung nach Neuinstallation
- 12 Monate Cloud-Historie
- Basis-Support für Link-Funktionen

Preisanker: knapp unter bzw. im Bereich etablierter Smart-Home-Link-Dienste.

### GC Pro — empfohlen 14,99 EUR/Monat oder 149 EUR/Jahr

- alles aus GC Link
- mehrere Grow-Central-Instanzen / Standorte
- Mehrbenutzerbetrieb und Rollen
- erweiterte Audit-Historie
- unbegrenzte oder sehr lange Cloud-Historie mit Fair-Use-Limit
- automatisierte CSV/JSON-Exporte
- Reports
- erweiterte Energie-/Kostenanalyse
- priorisierter Support für Pro-Funktionen

### Kein Tarifwildwuchs zum Start

Zum öffentlichen Start nur Core + Link. Pro erst freigeben, wenn Multi-Site/RBAC/Reports tatsächlich stabil sind. Kein Verkauf unfertiger Versprechen.

## 5. Hardwaremodell

### Zulässige strategische Richtung

Kein eigenes fertig montiertes elektronisches Grow-Central-Gerät als Kernmodell.

Möglich:

- Raspberry Pi als unverändertes Handelsprodukt,
- Original-Netzteil, SD-Karte, Gehäuse,
- handelsübliche ESP32-/Seeed-/Waveshare-Komponenten,
- Sensorplatinen und Kabel,
- optionale DIY-Stücklisten / Bundles,
- gedruckte oder digitale Aufbauanleitungen,
- Software-Image / Installationsanleitung getrennt.

### Wichtige Grenze

Ein DIY-Bundle beseitigt Produkthaftung nicht. Als Händler/Distributor bestehen weiterhin Sicherheits-, Informations- und Rückrufpflichten. Wird ein Produkt unter eigener Marke in Verkehr gebracht oder technisch so verändert, dass Konformität betroffen sein kann, können Herstellerpflichten entstehen.

Daher:

- wenn möglich Originalverpackung und Originalkennzeichnung erhalten;
- keine elektrischen Komponenten als eigenes fertiges Gerät umetikettieren;
- keine Netzteile unbekannter Herkunft;
- Komponenten von EU-konformen Lieferketten;
- Lieferant, Charge/Bestellung und Produktkennung dokumentieren;
- klare DIY-Anleitung mit zulässigen Spannungen, Polarität und Anschlussbildern;
- keine Netzspannungs-DIY-Bausätze zum Start;
- 230-V-Schaltgeräte nur als fertige, konforme Markenprodukte integrieren, nicht selbst bauen.

## 6. Rechtliches Software-Schutzmodell

### 6.1 Open-Source-Lizenz ist kein vollständiger Haftungsschutz

Der MIT-Haftungsausschluss bleibt für den freien Quellcode sinnvoll, ersetzt aber weder zwingendes Verbraucherrecht noch Produkthaftungs-, Datenschutz- oder Sicherheitsanforderungen bei kommerzieller Bereitstellung.

### 6.2 Bezahlservice klar vom freien Core trennen

Vertraglich und technisch:

- Core = freie Softwarelizenz;
- GC Link/Pro = gesonderter Dienstleistungs-/Digitalproduktvertrag;
- Hardwareverkauf = gesonderter Kaufvertrag;
- Support = klarer Leistungsumfang.

Keine Formulierungen, die suggerieren, mit dem Kauf von Komponenten entstünde automatisch eine Garantie für Ernte, Pflanzenzustand oder Kompatibilität beliebiger Drittgeräte.

### 6.3 Haftungsgrenzen, die anwaltlich geprüft werden müssen

AGB sollten insbesondere regeln:

- keine Nutzung als lebens-, gesundheits- oder sonst sicherheitskritisches System;
- Automationen ersetzen keine angemessene menschliche Kontrolle;
- keine Garantie für Ertrag, Pflanzenqualität oder wirtschaftlichen Erfolg;
- Sensorwerte sind nur so genau wie die eingesetzte Hardware/Kalibrierung;
- Drittanbieter-APIs und Herstellerprotokolle können sich ändern;
- Internet-, Strom-, Funk- oder Drittgeräteausfälle können Funktionen beeinträchtigen;
- Nutzer muss für kritische Verbraucher sichere Hardware und geeignete Fallbacks verwenden;
- Haftungsbegrenzung für leichte Fahrlässigkeit nur im rechtlich zulässigen Umfang und mit Ausnahme wesentlicher Vertragspflichten;
- keine Klausel, die Haftung für Vorsatz, grobe Fahrlässigkeit oder Verletzung von Leben/Körper/Gesundheit unzulässig ausschließt.

### 6.4 Keine falschen Sicherheitsversprechen

Marketing und UI vermeiden Aussagen wie:

- „100 % sicher“
- „verhindert Schimmel garantiert“
- „schützt Pflanzen vor jedem Ausfall“
- „fehlerfreie Steuerung“

Besser:

- „lokale Automationen“
- „Alarmierung bei erkannten Grenzwertverletzungen“
- „Ausfallsicherheit durch lokalen Betrieb, soweit die lokale Hardware verfügbar ist“
- „Messwerte abhängig von Sensor und Kalibrierung“

### 6.5 Verbraucherrecht für digitale Produkte

Für entgeltliche digitale Dienste müssen insbesondere Bereitstellung, Vertragsmäßigkeit, Kompatibilität, Sicherheit und notwendige Updates berücksichtigt werden. Sicherheitsupdates müssen im relevanten Zeitraum bereitgestellt und angekündigt werden.

Daraus folgt für Grow-Central:

- definierte Support- und Updatepolitik;
- keine willkürliche Funktionsentfernung in bezahlten Tarifen;
- Versions-/Changelog-Historie;
- dokumentierte Migrationspfade;
- bei wesentlichen Änderungen rechtzeitige Kundeninformation.

### 6.6 Abo-Recht

Für online abschließbare B2C-Dauerschuldverhältnisse muss ein rechtskonformer Kündigungsprozess vorgesehen werden. Produktdesign:

- Account -> Vertrag -> Kündigen;
- unmittelbar erreichbare Kündigungsfunktion auf der Website;
- Kündigungsbestätigung auf dauerhaftem Datenträger/E-Mail;
- Vertragslaufzeit und Verlängerung vor Abschluss klar anzeigen;
- Jahresvertrag nicht unnötig kompliziert machen.

### 6.7 Datenschutz

Cloud ist Opt-in. Local-only darf ohne Cloudkonto funktionieren.

Cloud-Mindestprinzipien:

- Datenminimierung;
- EU-Hosting bevorzugen;
- TLS überall;
- verschlüsselte Secrets;
- getrennte Benutzer-/Geräte-Identitäten;
- kurze Standard-Retention, längere Historie nur als bewusstes Feature;
- Export und Löschung;
- Subprozessoren dokumentieren;
- Verzeichnis von Verarbeitungstätigkeiten;
- TOMs;
- Auftragsverarbeitungsvertrag für B2B-Fälle, soweit Grow-Central als Auftragsverarbeiter handelt;
- keine Werbe-Tracker im lokalen UI;
- nur technisch notwendige Browser-Speicherung ohne Consent; optionale Analytics/Marketing nur nach Rechtsprüfung und Einwilligung.

### 6.8 Sicherheitsorganisation / CRA-Vorbereitung

Grow-Central bereits 2026 so bauen, als gelte der volle Cyber Resilience Act:

- Security-Policy und Kontaktadresse;
- Coordinated Vulnerability Disclosure;
- Abhängigkeitsinventar / SBOM;
- signierte Releases und Updates;
- reproduzierbare Builds soweit möglich;
- eindeutige Versionsstände;
- Default-Secrets verboten;
- sichere Erstkonfiguration;
- minimale Netzwerkfreigaben;
- Update- und Rollback-Prozess;
- Security-Logging ohne unnötige personenbezogene Daten;
- Incident-Runbook;
- Verantwortlichkeit für CRA-Meldungen festlegen;
- ab sofort Verfahren für aktiv ausgenutzte Schwachstellen und schwere Sicherheitsvorfälle dokumentieren.

## 7. Cannabis-spezifische Vermarktungsgrenze

Grow-Central selbst ist Steuerungs-/Monitoringsoftware bzw. Horticulture-Technik. Trotzdem sollte Werbung nicht so gestaltet sein, dass sie rechtlich als unmittelbare oder mittelbare Werbung für Konsumcannabis verstanden werden kann.

Strategische Marketingregel:

- Produkt als Indoor-Horticulture-/Grow-Automation positionieren;
- keine Konsumwerbung;
- keine Verkaufsförderung für Cannabis selbst;
- keine Aussagen zur Weitergabe oder zum Handel;
- rechtmäßige Nutzung voraussetzen;
- Anleitungen auf Technik, Klima, Sensorik und Pflanzenumgebung begrenzen;
- Rechtslage des Zielmarkts nicht durch Produkttexte „interpretieren“.

## 8. Markt- und Wettbewerbsanalyse

### Wettbewerbsdruck

**Hoch** bei allgemeinem Smart Home.

**Mittel** bei günstiger Grow-Monitoring-Hardware.

**Niedriger** bei der Kombination aus local-first, Open Source, Grow-spezifischem UX, herstellerübergreifender Integration und optionaler Cloud.

### Relevante Vergleichsmodelle

- Home Assistant / Nabu Casa: Open-Source-/Local-Core plus optionaler Remote-/Backup-Dienst.
- Pulse Grow: Free + bezahlte Historie, Multi-User, Exporte und Multi-Location.
- klassische Grow-Controller: Hardware-first, oft herstellerspezifischer und teurer.

### Stärken von Grow-Central

- local-first;
- kein Cloudzwang;
- Open Source;
- PWA statt Signierungs-/App-Store-Abhängigkeit;
- Raspberry-Pi-/ESP-Ökosystem;
- mehrere Hersteller integrierbar;
- niedrige Einstiegskosten;
- DIY-freundlich;
- eigener Cloud-Dienst kann wiederkehrende Einnahmen erzeugen.

### Schwächen

- Supportaufwand kann bei heterogener DIY-Hardware explodieren;
- unterschiedliche Router/WLAN-/Sensorumgebungen;
- Drittanbieterprotokolle ändern sich;
- geringe Markenbekanntheit;
- Home Assistant kann für technisch versierte Nutzer bereits vieles abdecken;
- Cannabis-Nische ist regulatorisch und werblich sensibel.

### Chancen

- Nutzer wollen zunehmend lokal kontrollierbare Systeme;
- PWA reduziert Plattformkosten;
- Deutschland erlaubt privaten Eigenanbau im gesetzlichen Rahmen;
- Komponenten können ohne eigene Hardwareentwicklung genutzt werden;
- Community kann Integrationen beitragen.

### Risiken

- gesetzliche Änderungen;
- neue EU-Software-/Cybersicherheitsanforderungen;
- Hosting-/Supportkosten;
- Sicherheitsvorfall würde Vertrauen stark beschädigen;
- zu frühe Monetarisierung kann Open-Source-Community bremsen;
- zu viele unterstützte Geräte erhöhen Wartungsaufwand schneller als Umsatz.

## 9. Wahrscheinlichkeitsmodell

Diese Werte sind **Management-Schätzungen**, keine gemessenen Marktstatistiken. Sie setzen ein stabiles Produkt, deutsch/englische Dokumentation, aktive Community-Arbeit und verlässlichen Cloudbetrieb voraus.

### Produkt-Markt-Fit

- Wahrscheinlichkeit, dass ein klarer Nutzen für technisch interessierte Home-/Indoor-Grower besteht: **70–85 %**.
- Wahrscheinlichkeit, dass Nutzer Grow-Central einem rein herstellerspezifischen System vorziehen, wenn ihre Geräte unterstützt werden: **55–70 %**.
- Wahrscheinlichkeit, dass der kostenlose Core ausreichend attraktiv für organisches Community-Wachstum ist: **60–75 %**.

### Bezahlmodell

Nach stabiler Cloud und brauchbarer Nutzerbasis:

- Wahrscheinlichkeit für mindestens 5 % Free-to-Paid-Conversion: **60–75 %**.
- realistische Zielconversion mittelfristig: **6–12 %**.
- sehr guter Wert bei starker Remote-/Backup-Funktion: **12–18 %**.

### Reichweite

Bei konsequenter Open-Source-/Community-Distribution:

- 1.000 aktive Installationen innerhalb 24 Monaten: **55–70 %**.
- 10.000 aktive Installationen innerhalb 36 Monaten: **25–40 %**.
- 30.000 aktive Installationen innerhalb 36–48 Monaten: **8–18 %**.

### Umsatzwahrscheinlichkeit innerhalb von drei Jahren

Unter der Annahme, dass GC Link/Pro stabil verkauft werden:

- > 10.000 EUR wiederkehrender Jahresumsatz: **55–70 %**.
- > 50.000 EUR ARR: **30–45 %**.
- > 100.000 EUR ARR: **18–30 %**.
- > 250.000 EUR ARR: **8–15 %**.

Die größte Variable ist nicht der Tarifpreis, sondern Reichweite + Supportkosten.

## 10. Umsatzszenarien

### Konservativ

- 2.000 aktive Installationen
- 5 % zahlend
- 59 EUR Jahresumsatz pro zahlendem Nutzer
- rund 5.900 EUR ARR

### Basis

- 10.000 aktive Installationen
- 10 % zahlend
- 80 % Link zu 59 EUR/Jahr
- 20 % Pro zu 149 EUR/Jahr
- gewichteter Jahresumsatz pro zahlendem Nutzer ca. 77 EUR
- rund 77.000 EUR ARR

### Starkes Szenario

- 30.000 aktive Installationen
- 15 % zahlend
- 70 % Link / 30 % Pro
- gewichteter Jahresumsatz ca. 86 EUR
- rund 387.000 EUR ARR

Hardware-/Komponentenumsatz ist darin nicht enthalten.

## 11. Hardwareökonomie

DIY-Komponenten sollten **nicht** als primärer Gewinnmotor geplant werden.

Ziele:

- Beschaffung vereinfachen;
- bekannte kompatible Komponenten anbieten;
- Fehlkäufe reduzieren;
- Projekt finanzieren;
- moderater Deckungsbeitrag.

Empfehlung:

- Ziel-Rohmarge auf Komponenten/Bundles: grob 15–25 %, bevor Retouren, Zahlungsgebühren, Versand, Gewährleistung und Support abgezogen werden.
- kein Preiskampf mit Amazon/AliExpress;
- Mehrwert über geprüfte Kompatibilität, Stückliste, Dokumentation und bekannte Firmware.

## 12. Kostenmodell Cloud

Cloud muss pro Nutzer kostenseitig begrenzt bleiben.

Kostenblöcke:

- VPS/DB/Object Storage;
- Backups;
- E-Mail/Push;
- Zahlungsanbieter;
- Umsatzsteuer/Steuerberatung;
- Monitoring;
- Support;
- Sicherheitsupdates;
- Rechtsberatung/Versicherung.

Architekturziel: Ein kostenloser Local-only-Nutzer verursacht nahezu keine laufenden Serverkosten.

## 13. Supportmodell

Open Source bedeutet nicht kostenlosen Individualsupport.

### Community Support

- GitHub Issues/Discussions
- Wiki
- Diagnoseexport

### GC Link

Support nur für Account, Remotezugriff, Backup und Cloudfunktionen.

### GC Pro

Priorisierte Bearbeitung; keine Garantie für individuelle Drittanbieterhardware außerhalb der Kompatibilitätsliste.

Diese Grenze muss sichtbar sein, sonst wird ein 5,99-EUR-Abo zum persönlichen 24/7-Systemhaus. Das wäre wirtschaftlich bemerkenswert kreativ und ansonsten katastrophal.

## 14. Versicherungen / organisatorische Absicherung

Vor Verkauf:

- Betriebshaftpflicht prüfen;
- Vermögensschaden-/IT-Haftpflicht bzw. Cyberversicherung prüfen;
- Produkthaftpflicht für Komponentenhandel prüfen;
- getrennte geschäftliche Organisation/Unternehmensform steuerlich und haftungsrechtlich prüfen;
- Datenschutz-/Incident-Verantwortung definieren.

Eine GmbH/UG ersetzt weder Produktsicherheit noch persönliche Pflichten, kann aber Teil der Risikostruktur sein und sollte mit Steuer- und Rechtsberatung bewertet werden.

## 15. Technische Maßnahmen mit direktem Haftungsnutzen

- Automationen mit Safe Defaults;
- maximale/minimale Stellwerte;
- Watchdog und Offline-Erkennung;
- Änderungen protokollieren;
- Nutzerbestätigung bei riskanten Schaltvorgängen;
- keine automatischen 230-V-Geräteannahmen;
- Gerätefähigkeiten explizit erkennen;
- Rückfallebene bei Cloudverlust;
- Konfigurationsbackup vor Updates;
- Rollback;
- Update-Signaturprüfung;
- verständliche Warnungen statt stiller Fehler;
- Kalibrierstatus für Sensoren anzeigen;
- Zeitstempel/Alter von Messwerten sichtbar machen;
- keine Steuerentscheidung aus veralteten Daten ohne definierte Policy.

## 16. Launch-Gates

### Kein Bezahlstart bevor:

1. frisches Pi-Image reproduzierbar installiert;
2. First-Boot ohne manuelle Reparatur funktioniert;
3. Cloud-Link nach Reinstall sauber wiederherstellbar ist;
4. Backup + Restore real getestet ist;
5. Security-/Update-Prozess steht;
6. Datenschutzerklärung und AGB anwaltlich geprüft sind;
7. Kündigungs-/Widerrufsablauf implementiert ist;
8. Statuspage/Monitoring vorhanden ist;
9. Supportumfang klar definiert ist;
10. mindestens 30–50 externe Testinstallationen oder ein vergleichbarer belastbarer Feldtest vorliegen.

### GC Pro erst wenn:

- RBAC real getestet;
- Multi-Site stabil;
- Audit unveränderlich genug für den versprochenen Zweck;
- Datenexport und Löschung vollständig;
- Kosten pro Nutzer gemessen sind.

## 17. Empfohlener Markteintritt

### Phase 1 — Community Beta

- Core kostenlos
- keine Zahlungsdaten
- 30–50 aktive Tester
- Telemetrie nur freiwillig/opt-in
- Fokus auf Installierbarkeit, Gerätekompatibilität und Fehlerquote

### Phase 2 — GC Link Early Access

- 2–3 Monate kostenloser Link-Test für ausgewählte Nutzer
- reale Cloudkosten messen
- Zahlungsbereitschaft abfragen, ohne Features künstlich zu sperren

### Phase 3 — öffentlicher GC Link Start

- 5,99 EUR/Monat
- 59 EUR/Jahr
- 30 Tage Test ohne komplizierte Hürden
- Core bleibt kostenlos

### Phase 4 — Pro

Erst nach nachgewiesener Nachfrage nach Multi-Site, Rollen, Reports und API.

## 18. Entscheidungskennzahlen

Nach 6 Monaten öffentlicher Beta messen:

- aktive Installationen MAU;
- erfolgreiche First-Boot-Quote;
- Anteil Installationen mit Cloud-Link;
- 30-/90-Tage-Retention;
- Supporttickets pro 100 Nutzer;
- durchschnittliche Cloudkosten pro Link-Nutzer;
- Backup-Erfolgsquote;
- Restore-Erfolgsquote;
- Free-to-Trial;
- Trial-to-Paid;
- Churn;
- ARR;
- Sicherheitsvorfälle;
- unterstützte Geräte mit automatisierten Tests.

### Go-Kriterien

GC Link wirtschaftlich ausbauen, wenn:

- Trial-to-Paid >= 8 %;
- monatlicher Churn <= 3 %;
- Cloud-/Payment-Kosten <= 20 % vom Netto-Link-Umsatz;
- Supportaufwand <= ca. 20 Minuten pro zahlendem Nutzer und Jahr im Mittel;
- keine kritischen ungelösten Security-/Restore-Probleme.

## 19. Zusammenfassung

Das wirtschaftlich und rechtlich robusteste Modell ist:

**Open-Source Local Core + optionaler GC Link + später GC Pro + konservativer DIY-Komponentenhandel.**

Nicht empfohlen:

- Cloudpflicht;
- grundlegende lokale Steuerung hinter Paywall;
- eigenes Netzspannungs-Hardwareprodukt in Phase 1;
- Eigenmarken-Umetikettierung fremder Elektronik ohne vollständige Konformitätsprüfung;
- unbegrenzter Individualsupport in günstigen Tarifen;
- Vermarktung mit Ernte-/Sicherheitsgarantien;
- Bezahlstart vor Backup-/Restore- und Security-Reife.

Strategisches Ziel: Nutzer kaufen **Komfort, Remotezugriff, Datensicherheit und Zeitersparnis**, nicht die Erlaubnis, ihre eigene lokale Hardware weiter benutzen zu dürfen.
