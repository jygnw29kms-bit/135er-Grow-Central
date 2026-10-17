# GrowCentral Windows Backoffice – Architektur

Stand: 2026-10-17

## 1. Anbieter-/Betreiberstruktur

GrowCentral wird aktuell von **einer natürlichen Einzelperson** betrieben. Diese Information ist projektweit verbindlich und muss bei Rechts-, Vertrags-, Rechnungs-, Datenschutz- und Anbietertexten berücksichtigt werden. Es darf nirgends ohne tatsächliche Gründung eine GmbH, UG, GbR oder andere Gesellschaft suggeriert werden.

Die konkrete geschäftliche Bezeichnung, ladungsfähige Anschrift, Steuerdaten, USt-ID und ggf. Gewerbe-/Unternehmensangaben werden vor öffentlichem Bezahlstart aus einer zentralen Betreiberkonfiguration bezogen und nicht in mehreren Codebasen hardcodiert.

## 2. Ziel

Zusätzlich zum Plesk-Modul wird eine **native Windows-Backoffice-App** entwickelt. Sie ist die zentrale Arbeitsoberfläche für Vertragsverwaltung, Abrechnung, Kundenverwaltung, Zahlungen, Rechnungen, Provisionierung, Editionen und administrative Cloud-Funktionen.

Plesk bleibt eine servernahe Administrations- und Notfalloberfläche. Die Windows-App darf keine zweite Quelle der Wahrheit und keine parallele Buchhaltung erzeugen.

## 3. Technologiestack

- C#
- WinUI 3
- Windows App SDK
- MVVM
- native Windows-Desktopanwendung
- Ziel: Windows 11, mit Windows-10-Kompatibilität soweit durch Windows App SDK unterstützt
- signierte Installer/Updates vor öffentlicher Distribution

## 4. Eine Datenquelle

Autoritative Datenquellen:

1. GrowCentral Cloud Account-/Customer-Daten
2. GrowCentral Billing Service
3. Providerdaten Stripe / PayPal
4. GrowCentral Entitlement-/Provisioning-Service
5. GrowCentral Audit-Log

Die Windows-App nutzt ausschließlich abgesicherte Backoffice-APIs. Plesk und Windows verwenden dieselben Dienste und dieselben IDs.

Nicht erlaubt:

- eigene lokale Kundendatenbank als Master
- separate Vertragsnummernlogik in Windows
- lokale Änderung von Zahlungsstatus ohne Serverbestätigung
- Speicherung von Karten-/CVC-Daten
- direkte Datenbankzugriffe vom Windows-PC über das Internet

## 5. Funktionsumfang Windows-App

### Dashboard
- MRR / ARR
- aktive FREE / LINK / PRO Installationen
- Trials
- Past Due
- Kündigungen
- Zahlungen heute/Monat/Jahr
- freiwillige Unterstützungen
- offene Provisionierungsfehler
- Cloud-/Webhook-Status

### Kunden
- Kunde suchen/filtern
- Kontakt-/Rechnungsdaten
- Geräte/Pis
- Verträge
- Zahlungen
- Rechnungen
- Support-/Adminnotizen
- Audit-Historie
- Datenschutzexport-/Löschstatus

### Verträge
- FREE / LINK / PRO
- monatlich/jährlich
- Startdatum
- Trial
- Verlängerung
- Kündigung zum Periodenende
- Status
- Providerreferenzen
- Historie aller Vertragsänderungen

### Zahlungen
- Stripe
- PayPal
- erfolgreich/offen/fehlgeschlagen/erstattet
- Betrag, Steuer, Währung
- Providerreferenz
- keine Kartendaten

### Rechnungen
- Rechnungsnummer
- Leistungszeitraum
- Netto/Steuer/Brutto
- Zahlungsstatus
- Kunden-/Steuerdaten
- PDF-/Providerreferenz
- Export für Steuerberatung/Buchhaltung
- unveränderbare Historie nach Finalisierung

### Provisionierung
- Subscription -> Account -> Device -> Edition
- Soll-/Ist-Vergleich
- FREE / LINK / PRO
- letzte Synchronisation
- Fehler/Wiederholung
- Grace Period
- Ablauf/Kündigung
- manueller Admin-Override nur mit Audit-Eintrag und Berechtigung

### Geräte/Cloud
Alles, was das Plesk-Modul administrativ kann:
- Cloud-Core Status
- Admin-Service Status
- Plattformstatus
- Geräte
- Entitlements
- Featureflags
- letzte Verbindung
- Versionen
- Kompatibilitätsstatus
- HomeKit-/Plattformstatus
- sichere Diagnose

### Billing Provider
- Stripe Test/Live Status
- PayPal Sandbox/Live Status
- Webhookstatus
- letzte Events
- fehlerhafte Events
- Reconciliation
- Refund-Vorgänge

### Unterstützungen
Freiwillige Unterstützung bleibt strikt getrennt von Premium:
- einmalig
- wiederkehrend
- Betrag
- Provider
- keine Entitlement-Freischaltung

## 6. Authentifizierung

Die Windows-App erhält einen eigenen **Backoffice-Login**. Dieser ist nicht identisch mit dem lokalen GrowCentral-Pi-Login und nicht bloß ein wiederverwendeter Cloud-Endkundenlogin.

Ziel:
- kurzlebiges Access Token
- rotierbares Refresh Token
- sichere Speicherung über Windows Credential Manager / DPAPI-geschützte Mechanismen
- MFA für Backoffice verpflichtend vor öffentlichem Bezahlbetrieb
- Geräte-/Session-Widerruf
- keine API-Schlüssel im App-Binary

## 7. Rollen

Obwohl aktuell nur eine Einzelperson administriert, wird RBAC von Anfang an vorbereitet:

- Owner
- Billing
- Support
- ReadOnly

Aktuell kann nur Owner verwendet werden. Dadurch muss bei späterer Unterstützung durch Steuerberatung/Support nicht die Architektur neu gebaut werden.

## 8. Buchhaltungsgrenze

Die App ist zunächst **Backoffice- und Abrechnungsverwaltung**, nicht automatisch ein vollständiger Ersatz für steuerliche Buchhaltungssoftware.

Sie muss:
- vollständige Zahlungs-/Rechnungsdaten exportieren
- revisionssichere Änderungs-/Auditdaten liefern
- DATEV-/CSV-Export vorbereiten
- Storno/Korrekturbelege nachvollziehbar abbilden
- Providerabrechnungen abgleichen

Ob und wann eine GoBD-konforme Eigenbuchhaltung umgesetzt wird, wird separat juristisch/steuerlich geprüft. Bis dahin bleibt die steuerliche Buchführung in dafür geeigneter Buchhaltungssoftware bzw. bei Steuerberatung.

## 9. API-Struktur

Neue Backoffice-API, ausschließlich HTTPS:

- `GET /api/backoffice/dashboard`
- `GET /api/backoffice/customers`
- `GET /api/backoffice/customers/{id}`
- `GET /api/backoffice/contracts`
- `GET /api/backoffice/payments`
- `GET /api/backoffice/invoices`
- `GET /api/backoffice/provisioning`
- `GET /api/backoffice/devices`
- `GET /api/backoffice/webhooks`
- `POST /api/backoffice/contracts/{id}/cancel`
- `POST /api/backoffice/payments/{id}/refund`
- `POST /api/backoffice/provisioning/{id}/retry`
- `POST /api/backoffice/entitlements/{device_id}/override`

Alle schreibenden Aktionen:
- Auth
- CSRF nicht relevant für native Bearer-API, aber Tokenbindung/Origin-Modell beachten
- RBAC
- idempotency key
- Audit-Log
- serverseitige Validierung

## 10. Offlineverhalten

Die Windows-App darf lesbare Daten verschlüsselt cachen, aber keine offline erzeugten Vertrags-/Zahlungsänderungen als endgültig behandeln.

Offline:
- Dashboard aus Cache lesbar
- Kunden/Verträge lesbar soweit gecacht
- keine Zahlung freigeben
- keine Edition dauerhaft ändern
- keine Kündigung als erfolgreich anzeigen, bevor Server bestätigt

## 11. UI

Die App verwendet das GrowCentral-Designsystem:
- futuristisch/technisch
- kein generischer AI-Look
- native Windows-Interaktion
- klare Tabellen und Detailseiten
- SVG/vektorbasierte Statusgrafiken
- Dark Mode als Hauptmodus, Light optional
- JL1976/GrowCentral Branding gemäß Projektvorgaben

## 12. Plesk vs Windows

Plesk:
- Serverstatus
- Notfall-/Fallback-Administration
- Provisioning/Billing-Basis
- Servicekonfiguration
- Adminzugriff direkt am Server

Windows-App:
- tägliche Backoffice-Arbeit
- Kunden
- Verträge
- Rechnungen
- Zahlungen
- Auswertungen
- Provisionierungsübersicht
- Support-/Auditansicht
- Provider-Reconciliation

Funktionsparität bedeutet: Alles fachlich Relevante des Plesk-Moduls ist auch über Windows verfügbar. Server-/Plesk-spezifische Aktionen wie Dateimanager oder SSH-Terminal bleiben Plesk-spezifisch.

## 13. Sicherheitsregel

Die Windows-App kommuniziert niemals direkt mit PostgreSQL, Plesk-internen Ports oder Stripe-/PayPal-Secrets. Sie spricht ausschließlich die öffentliche abgesicherte Backoffice-API. Provider-Secrets bleiben serverseitig.

## 14. Umsetzungsreihenfolge

1. zentrale Betreiber-/Legal-Konfiguration
2. Billing-/Provisioning-Datenmodell finalisieren
3. Backoffice-API
4. Backoffice-Authentifizierung + MFA
5. native WinUI-3-App Grundgerüst
6. Dashboard/Kunden/Verträge
7. Zahlungen/Rechnungen
8. Provisionierung/Geräte
9. Provider-Reconciliation
10. Export/DATEV-Vorbereitung
11. Installer/Signierung/Updatekanal
12. Testbetrieb gegen Stripe-Testmode + PayPal Sandbox

## 15. Verbindliche Projektregel

GrowCentral ist aktuell ein von **einer Einzelperson betriebenes Projekt**. Alle Systeme müssen geringe administrative Last, Automatisierung, nachvollziehbare Abläufe und möglichst wenig manuelle Doppelpflege priorisieren.
