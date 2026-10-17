# GrowCentral Backoffice – Implementierungsstatus

Stand: 2026-10-17

## Implementiert auf `feature/business-documents-backoffice`

### Gemeinsame Domain
- .NET 8 plattformneutral, damit Windows-App und Server dieselben fachlichen Regeln verwenden.
- 47 Geschäftsdokumenttypen.
- B2B/B2C/Internal/Behörde/Personal-Geltungsbereiche.
- Pflichtfelder und dokumenttypspezifische Rechtsbezüge.
- kontrollierte Statusübergänge.
- Inhalts- und Link-Sperre nach Finalisierung.
- Korrekturbeleg verändert den Ursprungsbeleg erst nach erfolgreicher Finalisierung der Korrektur.
- serverseitig definierte Nummernkreis-Policies für alle Dokumenttypen.
- dokumentierte Freigabepflicht für rechtlich sensible Dokumente.

### Authentifizierung / MFA / Rollen
- serverseitige Benutzerverwaltung in PostgreSQL.
- Rollen `Owner`, `Billing`, `Support`, `ReadOnly` mit serverseitiger Berechtigungsprüfung.
- Passwörter ausschließlich als PBKDF2-SHA256-Hash mit Salt und 210.000 Iterationen.
- TOTP-MFA für Backoffice-Benutzer.
- MFA-Secrets AES-GCM-verschlüsselt mit getrenntem 32-Byte-Server-Master-Key.
- zusätzliche Benutzer bleiben bis zur eigenen erfolgreichen TOTP-Bestätigung im Enrollment-Zustand und können sich vorher nicht regulär anmelden.
- produktiver Session-Endpunkt gibt 30-Minuten-Access-Tokens plus 30-Tage-Refresh-Tokens aus.
- Access- und Refresh-Tokens werden in PostgreSQL nur als SHA-256-Hash gespeichert.
- Refresh-Tokens werden bei jeder Erneuerung rotiert; das vorherige Refresh-Token ist danach nicht mehr verwendbar.
- Logout widerruft die Sitzung und entfernt den aktiven Refresh-Hash.
- Auth-Audit für Bootstrap, Benutzeranlage, MFA-Bestätigung, Login, Refresh-Rotation und Logout.
- Rate-Limit für Login, Enrollment, Refresh und Bootstrap.
- Bootstrap-Token kann nur die erste Owner-Anlage autorisieren und ersetzt keine normale Sitzungsauthentifizierung.
- der ältere `/auth/login`-Pfad bleibt vorübergehend kompatibel, erhält aber ebenfalls nur ein kurzlebiges Access-Token; produktiver Client-Zielpfad ist `/auth/session` plus `/auth/refresh`.

### Betreiber- / Steuerkonfiguration
- Rechtsform im Projekt verbindlich `sole_proprietor` / Einzelunternehmen.
- Stammdaten für rechtlichen Namen, Geschäftsbezeichnung, Anschrift, Steuernummer, USt-IdNr., Wirtschafts-IdNr. und Finanzamt.
- Regelbesteuerung/Kleinunternehmer, USt-Voranmeldungszeitraum, Soll-/Ist-Versteuerung sowie SKR03/SKR04 konfigurierbar.
- Plausibilitätsregeln für § 19 UStG, insbesondere 25.000-EUR-Vorjahresgrenze und 100.000-EUR-Grenze im laufenden Jahr.
- Hinweise für Verzicht/Bindungsfrist und widersprüchliche Steuerkonfigurationen.
- Änderungen der Betreiber-/Steuerkonfiguration werden auditiert.

### Rechnung / E-Rechnung
- E-Rechnungsentscheidung als eigene Domainregel.
- Übergangsregel bis 31.12.2026 abgebildet.
- zusätzliche Übergangsregel bis 31.12.2027 bei Vorjahresumsatz bis 800.000 EUR abgebildet.
- Ausnahmen für Kleinbetragsrechnungen bis 250 EUR, Kleinunternehmerrechnungen, Fahrausweise und die einschlägigen steuerfreien Umsätze nach § 4 Nr. 8 bis 29 UStG modelliert.
- Kleinunternehmer-Ausnahme betrifft die Ausstellung; E-Rechnungs-Empfangsfähigkeit bleibt im Zielbild erhalten.
- B2G wird bewusst als separater Regelpfad behandelt.
- einfache PDF-Rechnung wird nicht als strukturierte E-Rechnung behandelt.
- Zielmatrix Stand 17.10.2026: XRechnung 3.0.2, KoSIT-Validator 1.6.3, ZUGFeRD 2.5.2, EN 16931.

### Mahnwesen
- Verbraucher: 40-EUR-Verzugspauschale blockiert.
- Standard-Verzugszinsprüfung B2C/B2B vorbereitet.
- Mahndokumente bleiben mit Forderungs-/Rechnungsreferenz verknüpfbar.

### Doppelbuchungs-Ledger
- Buchungsentwürfe mit Soll/Haben-Zeilen und Beleg-/Geschäftspartnerreferenzen.
- Soll und Haben müssen centgenau ausgeglichen sein.
- negative Buchungsbeträge werden nicht als nachträgliche Mutation akzeptiert; Korrekturen erfolgen über Gegenbuchungen.
- PostgreSQL-Journal und Journalzeilen sind nach Verbuchung unveränderbar.
- eindeutige Buchungsnummern über den zentralen Nummernkreis.
- Buchungsperioden `open`, `closing`, `locked`, `reopened`.
- gesperrte/abschließende Perioden nehmen keine Buchungen an.
- Wiedereröffnung nur durch Owner mit nachvollziehbarer Begründung und Audit.
- Konten unterstützen SKR03/SKR04; konkrete Konten-Mappings werden noch fachlich vervollständigt.

### Eingangsbelege / Originalarchiv
- separates persistentes Originalbeleg-Volume, getrennt von Geräte-/Telemetriedaten.
- Originaldatei wird unverändert archiviert; Metadaten und SHA-256-Prüfsumme liegen in PostgreSQL.
- Dublettenerkennung über SHA-256.
- Speicherpfad wird aus der Prüfsumme erzeugt, nicht aus dem übermittelten Dateinamen.
- Größenlimit 25 MiB.
- zugelassene Typen: PDF, XML, JPEG, PNG.
- Dateisignatur/Inhaltsprüfung gegen den deklarierten MIME-Typ vor Archivierung.
- Originalbelegtabelle ist append-only.
- Workflowstatus getrennt vom unveränderbaren Original.
- Mindestaufbewahrung, Legal-Hold und verpflichtende Löschprüfung sind im Schema vorgesehen; keine automatische Löschung nur aufgrund eines Datums.

### Persistenz / Audit
- separates PostgreSQL-Schema für kaufmännische Daten.
- Geschäftspartner, Dokumente und Dokumentverknüpfungen.
- unveränderbare Dokumentrevisionen.
- append-only Audit-Events.
- atomare Nummernkreisvergabe.
- Idempotency-Keys.
- Periodenstatus und Wiedereröffnungsdaten.
- Schutz gegen Löschen finalisierter Dokumente.

### Backoffice API
- ASP.NET Core / .NET 8 und PostgreSQL über Npgsql.
- Authentifizierung mit TOTP-MFA, RBAC, kurzlebigem Access-Token und rotierendem Refresh-Token.
- bestätigter MFA-Enrolment-Endpunkt für zusätzliche Benutzer.
- Dokumenttyp-Katalog, Rechnungs-Compliance und Dokumentvalidierung.
- serverseitige Dokumentnummernvergabe, Entwurf, Lesen, Freigabe und Finalisierung.
- Betreiber-/Steuerkonfiguration inklusive Validierung.
- Ledger-Konten, Buchungsvalidierung, Buchung, Periodensperre und begründete Wiedereröffnung.
- Originalbeleg-Upload, Metadatenabruf und authentifizierter Originalabruf.
- unveränderbare Finalrevision mit SHA-256-Inhaltshash.

### Deployment
- eigener gehärteter Container für Backoffice API.
- PostgreSQL als separater Container und internes Datenbanknetz.
- separates persistentes Volume für Originalbelege.
- Basis-Schema plus Ledger-, Beleg- und Auth-Hardening-Migrationen für frische Installationen.
- API nur an `127.0.0.1:8091`; Veröffentlichung ausschließlich über abgesicherten Reverse Proxy vorgesehen.
- bestehende Python/SQLite-Cloud für Geräte/Telemetrie bleibt getrennt.

### CI
- Domain-Tests auf Linux/.NET 8.
- gesonderte API-Tests für Passwort-Hashing, TOTP, MFA-Secret-Verschlüsselung, RBAC und Steuerkonfiguration.
- Tests für E-Rechnungs-Ausnahmen/Versionsmatrix, Beleg-Dateisignaturen und Doppelbuchungsregeln.
- API-Restore und Release-Build.
- Docker-Compose-Validierung und echter Docker-Image-Build.
- vorhandene Repository-Python-, Security- und Domain-Checks bleiben aktiv.

## Rechts-/Normstand, der im Code berücksichtigt ist

- § 14 UStG / § 27 Abs. 38 UStG: E-Rechnung und Übergangsfristen.
- § 19 UStG: Kleinunternehmergrenzen 25.000 EUR Vorjahr / 100.000 EUR laufendes Jahr.
- §§ 33, 34, 34a UStDV: Kleinbetrag, Fahrausweis, Kleinunternehmerrechnung.
- §§ 286, 288 BGB: Verzug, Verzugszinsen und 40-EUR-Pauschale.
- GoBD in der Fassung nach der zweiten Änderung vom 14.07.2025.
- achtjährige Mindestaufbewahrung für Rechnungen/Buchungsbelege nach aktueller Rechtslage, ohne automatische Löschannahme bei fortbestehender steuerlicher Relevanz.

## Noch nicht produktionsfreigegeben

Die folgenden Punkte bleiben verbindliche Release-Gates:

1. reale Betreiber-/Steuerdaten eintragen und fachlich gegen tatsächliche Finanzamts-/Unternehmensdaten prüfen.
2. vollständige EN-16931-Erzeugung und externe Schematron-/KoSIT-Validierung für XRechnung 3.0.2.
3. echte ZUGFeRD-2.5.2-Erzeugung und Validierung inklusive PDF/A-3-Anforderungen.
4. strukturierte E-Rechnungsinhalte sicher visualisieren und fachlich klassifizieren, ohne das Original zu verändern.
5. Eingangsbeleg-Klassifizierung, Rechnungsdatenextraktion, Dubletten-/Plausibilitätsprüfung und Buchungsvorschläge.
6. SKR03/SKR04-Kontenstamm und rechtlich/fachlich geprüfte automatische Buchungsregeln.
7. Bank/Stripe/PayPal-Reconciliation.
8. USt-Ledger, Vorsteuerlogik und UStVA-Referenzfälle.
9. Monatsabschluss vollständig verdrahten und Abschluss-Checkliste automatisieren.
10. EÜR, Anlagenverzeichnis/AfA und DATEV-Export.
11. Migrationstooling für bereits bestehende PostgreSQL-Volumes; `docker-entrypoint-initdb.d` reicht nur für Neuinstallationen.
12. Backup-/Restore-Nachweis einschließlich Originalbeleg-Volume und Prüfsummenprüfung.
13. Verfahrensdokumentation automatisiert aus Software-, Schema- und Regelversionen erzeugen.
14. WinUI-3-Client gegen die Backoffice API.
15. Installer, Signierung und sicherer Updatekanal.
16. abschließende fachliche Steuer-/Rechtsprüfung vor erstem realen Geschäftsbetrieb.

## Verbindliche Sicherheitsgrenze

Der Dienst bleibt bis zum Abschluss der verbliebenen Release-Gates nur lokal bzw. hinter der vorgesehenen abgesicherten Verwaltungsstrecke erreichbar. Die implementierten Rechtsregeln sind technische Schutzregeln und ersetzen keine individuelle steuerliche oder anwaltliche Prüfung der realen Unternehmensdaten und Vertragsfälle.
