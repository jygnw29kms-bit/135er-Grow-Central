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

### Rechnung / E-Rechnung
- E-Rechnungsentscheidung als eigene Domainregel.
- Übergangsregel bis 31.12.2026 abgebildet.
- zusätzliche Übergangsregel bis 31.12.2027 bei Vorjahresumsatz bis 800.000 EUR abgebildet.
- strukturierte Formate im System: XRechnung, ZUGFeRD EN16931, sonstiges EN16931.
- B2G wird bewusst als separater Regelpfad behandelt.
- einfache PDF-Rechnung wird nicht als strukturierte E-Rechnung ausgegeben.

### Mahnwesen
- Verbraucher: 40-EUR-Verzugspauschale blockiert.
- Standard-Verzugszinsprüfung B2C/B2B vorbereitet.
- Mahndokumente bleiben mit Forderungs-/Rechnungsreferenz verknüpfbar.

### Persistenz
- separates PostgreSQL-Zielschema für kaufmännische Daten.
- Geschäftspartner.
- Dokumente.
- Dokumentverknüpfungen.
- unveränderbare Dokumentrevisionen.
- append-only Audit-Events.
- atomare Nummernkreisvergabe.
- Idempotency-Keys.
- Periodenstatus und Wiedereröffnungsdaten.
- Schutz gegen Löschen finalisierter Dokumente.

### Backoffice API
- ASP.NET Core / .NET 8.
- PostgreSQL über Npgsql.
- Health-Endpunkt.
- Dokumenttyp-Katalog.
- Rechnungs-Compliance-Prüfung.
- Dokumentvalidierung.
- serverseitige Dokumentnummernvergabe.
- Entwurf anlegen/lesen.
- dokumentierte Freigabe mit Begründung + Audit.
- Finalisierung mit optimistischer Versionsprüfung.
- unveränderbare Finalrevision mit SHA-256-Inhaltshash.
- Idempotency für schreibende Kernvorgänge.
- Bootstrap-Admin-Token nur als Entwicklungsstufe; API meldet ausdrücklich `production_auth_ready=false`.

### Deployment
- eigener gehärteter Container für Backoffice API.
- PostgreSQL als separater Container.
- internes Datenbanknetz.
- API nur an `127.0.0.1:8091`; Veröffentlichung ausschließlich über Reverse Proxy vorgesehen.
- bestehende Python/SQLite-Cloud für Geräte/Telemetrie bleibt getrennt und unverändert.

### CI
- Domain-Tests auf Linux/.NET 8.
- API-Restore und Release-Build.
- Docker-Compose-Validierung.
- vorhandene Repository-Security-/Domain-Checks bleiben aktiv.

## Noch nicht produktionsfreigegeben

Die folgenden Punkte sind bewusste Release-Gates und dürfen vor echtem Geschäftsbetrieb nicht übersprungen werden:

1. Backoffice-Login mit kurzlebigen Access-Tokens und rotierenden Refresh-Tokens.
2. MFA für Owner/Backoffice.
3. RBAC Owner/Billing/Support/ReadOnly.
4. echte operator-/steuerliche Stammdaten statt Platzhalter.
5. vollständige Rechnungserzeugung inkl. EN16931-Semantikvalidierung und XRechnung/ZUGFeRD-Ausgabe.
6. strukturierten E-Rechnungs-Originaldatensatz archivieren und visualisieren.
7. Eingangsbeleg-Workflow.
8. Ledger/Buchungsengine und Kontenmapping.
9. Bank/Stripe/PayPal-Reconciliation.
10. USt-Ledger und UStVA-Referenzfälle.
11. Monatsabschluss und Periodensperren vollständig verdrahten.
12. EÜR/Anlagen/AfA/DATEV.
13. Backup-/Restore-Nachweis und Integritätsprüfung.
14. Verfahrensdokumentation automatisiert aus Software-/Regelversionen erzeugen.
15. fachliche Prüfung der realen Steuerkonfiguration des Betreibers.
16. WinUI-3-Client gegen die Backoffice API.
17. Installer, Signierung und Updatekanal.

## Verbindliche Sicherheitsgrenze

Bis die Produktionsauthentifizierung inklusive MFA und RBAC umgesetzt und geprüft ist, wird der Backoffice-Dienst nicht öffentlich als produktives Verwaltungsinterface freigegeben. Der Bootstrap-Token ist nur eine kontrollierte Entwicklungsbrücke.
