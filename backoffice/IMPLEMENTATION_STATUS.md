# GrowCentral Vertragsabrechnung – Implementierungsstatus

Stand: 2026-10-17

## Verbindlicher Produktscope

Das Backoffice ist **keine allgemeine Finanzbuchhaltung und kein ERP**. Es dient ausschließlich der kaufmännischen Abwicklung der **GrowCentral-Verträge**.

Der Betreiber ist verbindlich als **Einzelunternehmen / sole proprietor** modelliert. Keine AG, keine Konzernstruktur, keine Gesellschafter-/Aktienverwaltung und keine AG-spezifische Rechnungslegung.

Verbindliche Prozesskette:

`Kunde -> GrowCentral-Vertrag -> Abrechnungsperiode -> Rechnung -> Zahlung -> ggf. Mahnung/Korrektur -> steuerliche Auswertung`

Jede interne Buchung muss auf einen GrowCentral-Vertrag und zusätzlich auf Rechnung/Zahlung/Korrektur zurückführbar sein. Freie allgemeine Unternehmensbuchungen sind technisch außerhalb des zulässigen Scopes.

## Implementiert auf `feature/business-documents-backoffice`

### Authentifizierung / MFA / Rollen
- PostgreSQL-Benutzerverwaltung.
- Rollen `Owner`, `Billing`, `Support`, `ReadOnly`.
- PBKDF2-SHA256-Passworthashes mit Salt und 210.000 Iterationen.
- TOTP-MFA; MFA-Secrets AES-GCM-verschlüsselt.
- bestätigtes MFA-Enrolment für zusätzliche Benutzer.
- 30-Minuten-Access-Tokens plus rotierende 30-Tage-Refresh-Tokens; serverseitig nur Hashes gespeichert.
- Login-/Enrollment-/Refresh-Rate-Limits und Auth-Audit.
- Bootstrap-Token nur für die erste Owner-Anlage.

### Betreiber / Steuerstatus
- Rechtsform verbindlich `sole_proprietor`.
- rechtlicher Name, Geschäftsbezeichnung, Anschrift, Steuernummer, USt-ID, Wirtschafts-ID und Finanzamt.
- Regelbesteuerung/Kleinunternehmer sowie Ist-/Sollversteuerung konfigurierbar.
- Plausibilitätsregeln für § 19 UStG.
- keine gesellschaftsrechtlichen oder AG-spezifischen Felder/Funktionen.

### GrowCentral-Verträge
- eigenes persistentes Vertragsmodell `backoffice_gc_contracts`.
- Vertragsnummer, Kunde, Produkt/Tarif, Abrechnungsintervall, Betrag, Steuer, Laufzeit und Status.
- eigene Abrechnungsperioden `backoffice_gc_billing_periods`.
- Rechnung kann eindeutig einer Vertragsperiode zugeordnet werden.
- Zahlungen `backoffice_gc_payments` sind zwingend mit Vertrag und Rechnung verknüpft.
- Zahlungsprovider sind nur Bank/Stripe/PayPal/manuell im Zusammenhang mit GC-Rechnungen.

### Rechnungen / E-Rechnung
- kontrollierte Finalisierung und unveränderbare Finalrevisionen.
- serverseitige Nummernkreise.
- Korrektur/Storno ohne nachträgliches Überschreiben des Ursprungsbelegs.
- deutsche E-Rechnungs-Übergangsregeln 2025-2027 und relevante Ausnahmen modelliert.
- Zielmatrix Stand 17.10.2026: XRechnung 3.0.2, KoSIT-Validator 1.6.3, ZUGFeRD 2.5.2, EN 16931.

### Zahlungen / Forderungen / Mahnwesen
- Zahlungen werden einer GC-Rechnung und damit einem GC-Vertrag zugeordnet.
- Providergebühren dürfen nur als Teil einer konkreten GC-Zahlung verarbeitet werden.
- offene Forderungen, Zahlungserinnerungen und Mahnungen beziehen sich ausschließlich auf GC-Rechnungen.
- B2B/B2C-Regeln; keine 40-EUR-Verzugspauschale gegen Verbraucher.

### Interne Buchungsmechanik
- centgenaue Soll/Haben-Prüfung.
- unveränderbare Journalbuchungen und Gegenbuchungen statt Editieren.
- Periodensperren und auditierte Wiedereröffnung.
- **Scope-Guard im Domaincode:** `ContractId` ist zwingend; zusätzlich Rechnung/Dokument oder Zahlung.
- Abrechnungsbuchungen benötigen eine `BillingPeriodId`, außer Zahlung oder Gegenbuchung.
- **Scope-Guard in PostgreSQL:** Journalzeilen außerhalb des GC-Vertragsbezugs werden durch Constraints blockiert.
- das Ledger ist interne Abrechnungstechnik und kein frei nutzbares Buchhaltungsmodul.

### Aus dem Scope entfernt
- allgemeine Kreditoren-/Lieferantenbuchhaltung.
- allgemeiner Eingangsbeleg-Upload und Lieferantenbelegarchiv.
- Einkaufsbestellungen/Beschaffung.
- allgemeine Privatentnahmen/-einlagen-Verwaltung.
- eigenständige Anlagen-/AfA-Buchhaltung.
- Lohn-/Gehaltsbuchhaltung.
- allgemeine Kassen-/Bankbuchhaltung.
- beliebige manuelle Journalbuchungen ohne GC-Vertragsbezug.
- allgemeiner DATEV-/ERP-Ersatz für das gesamte Unternehmen.
- Aktien-, Gesellschafter-, Konzern- oder AG-Funktionen.

### Deployment
- ASP.NET Core / .NET 8 Backoffice API.
- separates PostgreSQL für Vertragsabrechnung.
- bestehende Geräte-/Telemetrie-Cloud bleibt getrennt.
- frische DB installiert Basis-Schema, internes Ledger, GC-Vertragsabrechnung und Auth-Hardening.
- allgemeines Lieferantenbeleg-Volume und entsprechende API wurden wieder entfernt.
- API nur auf `127.0.0.1:8091`, Veröffentlichung später ausschließlich abgesichert.

### CI
- Domain-Tests für Dokumente, E-Rechnung und interne Buchungsregeln.
- explizite Tests, dass freie Buchungen ohne `ContractId`/Rechnungsquelle abgelehnt werden.
- API-Tests für Passwort-Hashing, MFA, RBAC und Steuerkonfiguration.
- Release-Build, Compose-Validierung und Docker-Image-Build.
- Repository-Python-, Security- und Domain-Checks bleiben aktiv.

## Rechts-/Normstand im relevanten Scope

- § 14 UStG / § 27 Abs. 38 UStG: Rechnungen und E-Rechnung.
- § 19 UStG: Kleinunternehmerregelung.
- §§ 33, 34, 34a UStDV: besondere Rechnungsfälle.
- §§ 286, 288 BGB: Zahlungsverzug und Mahnwesen.
- GoBD für die nachvollziehbare, unveränderbare Verarbeitung der GC-Abrechnungsdaten.

## Verbleibende Release-Gates

1. reale Betreiber-/Steuerdaten eintragen und fachlich prüfen.
2. produktives Vertrags-API für Anlegen/Ändern/Kündigen/Versionieren der GC-Verträge.
3. automatische Erzeugung der Abrechnungsperioden aus den Verträgen.
4. automatische Rechnungserzeugung aus Vertrags-/Periodendaten.
5. vollständige EN-16931-/XRechnung-3.0.2-Erzeugung und KoSIT-Validierung.
6. ZUGFeRD-2.5.2/PDF-A-3, soweit benötigt.
7. Bank/Stripe/PayPal-Reconciliation ausschließlich für GC-Rechnungen.
8. Umsatzsteuer-Auswertung ausschließlich aus der GC-Vertragsabrechnung.
9. periodischer GC-Abrechnungsabschluss mit Forderungs-/Zahlungsabgleich.
10. Backup-/Restore-Nachweis für Vertrags-, Rechnungs- und Zahlungsdaten.
11. Verfahrensdokumentation für den GC-Abrechnungsprozess.
12. WinUI-3-Client für Kunden, Verträge, Abrechnungen, Rechnungen, Zahlungen und Mahnungen.
13. Installer, Signierung und sicherer Updatekanal.
14. abschließende fachliche Steuer-/Rechtsprüfung vor realem Geschäftsbetrieb.

## Verbindliche Sicherheits- und Scope-Grenze

Das Backoffice darf nicht schleichend zu einer allgemeinen Buchhaltungs- oder ERP-Lösung erweitert werden. Neue kaufmännische Funktionen sind nur zulässig, wenn sie unmittelbar für die Abrechnung eines GrowCentral-Vertrags, dessen Rechnung, Zahlung, Korrektur oder steuerliche Auswertung erforderlich sind.
