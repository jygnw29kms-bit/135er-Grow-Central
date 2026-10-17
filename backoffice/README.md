# GrowCentral Backoffice / Buchhaltung

## Verbindliche Architektur

Die native Windows-App ist **eine einzige kaufmännische Anwendung** für Buchhaltung, Abrechnung und sämtliche Geschäftsdokumente. Es gibt kein separates Vorlagenprogramm und keine zweite Datenhaltung.

### Module

1. **Dashboard**
   - Umsätze, offene Posten, Zahlungen, Kosten, USt, Liquidität
   - offene Aufgaben und Freigaben
   - nicht abgeglichene Bank-/Stripe-/PayPal-Vorgänge

2. **Buchhaltung**
   - Journal / Ledger
   - Kontenrahmen SKR03/SKR04 konfigurierbar
   - Buchungssätze
   - Privatentnahmen/-einlagen
   - Steuerbuchungen
   - Periodensperren und Abschluss

3. **Belege**
   - Eingangsrechnungen
   - PDF/Bild/XML/ZUGFeRD/XRechnung
   - Originaldatei unverändert archivieren
   - Kontierung, Steuer, Zahlungsstatus
   - Duplikaterkennung

4. **Ausgangsrechnungen**
   - Rechnung, Abschlag, Schlussrechnung
   - Korrektur/Storno
   - E-Rechnung EN 16931 / XRechnung / ZUGFeRD
   - Zahlungs- und Mahnstatus
   - Verknüpfung mit Vertrag, Kunde und Buchung

5. **Geschäftsdokumente**
   - Angebote
   - Auftragsbestätigungen
   - Lieferscheine
   - Leistungsnachweise
   - Abnahmeprotokolle
   - Mahnungen
   - Reklamationen
   - Verträge
   - Datenschutzdokumente
   - Behördenkorrespondenz
   - interne Freigaben
   - Verfahrensdokumentation

   Diese Dokumente verwenden das gemeinsame `BusinessDocument`-Modell und werden, sobald buchhaltungsrelevant, direkt mit Rechnung/Buchung/Beleg verknüpft.

6. **Kunden & Lieferanten**
   - Stammdaten
   - Rechnungsadressen
   - Steuerdaten
   - Verträge
   - Dokumente
   - offene Posten
   - Zahlungs-/Kommunikationshistorie

7. **Bank / Stripe / PayPal**
   - Import/Sync
   - Reconciliation
   - Gebühren
   - Refunds
   - Chargebacks
   - Zuordnung zu Rechnungen und Buchungen

8. **Mahnwesen**
   - Zahlungserinnerung
   - Mahnstufen
   - gesetzliche Verzugszinsen
   - B2B/B2C-Unterscheidung
   - keine 40-EUR-Verzugspauschale gegen Verbraucher
   - Übergabe an gerichtliches Mahnverfahren nur nach manueller Freigabe

9. **Steuern**
   - Umsatzsteuer-Ledger
   - UStVA-Vorschau
   - EÜR
   - Anlagen/AfA
   - DATEV-Export
   - später ERiC/ELSTER

10. **Monatsabschluss**
    - Bankabgleich
    - Providerabgleich
    - offene Belege
    - Rechnungen
    - Gebühren
    - Steuerabgleich
    - EÜR
    - Abschlussbericht
    - Periodensperre

11. **Audit / Archiv**
    - jede relevante Änderung versioniert
    - finalisierte Dokumente unveränderbar
    - Korrekturen nur über Storno/Korrektur
    - Hash/Integritätsprüfung
    - Export für Prüfung

12. **Einstellungen**
    - Betreiberdaten
    - Steuerstatus
    - USt-ID / Steuernummer / Wirtschafts-ID
    - Finanzamt
    - Ist-/Sollversteuerung
    - UStVA-Zeitraum
    - Kontenrahmen
    - Nummernkreise
    - E-Rechnungsformat
    - Bank/Stripe/PayPal
    - Rollen und MFA

## Eine Quelle der Wahrheit

Alle Module greifen auf dieselben Cloud-Dienste und IDs zu. Die Windows-App ist niemals eine eigene Buchhaltungsdatenbank.

Gemeinsame Verknüpfung:

`Kunde -> Vertrag/Auftrag -> Geschäftsdokument -> Rechnung -> Zahlung -> Buchung -> Steuerperiode -> Abschluss`

und für Einkauf:

`Lieferant -> Bestellung -> Eingangsbeleg -> Zahlung -> Buchung -> Vorsteuer -> Abschluss`

## Geschäftsdokumente + Buchhaltung

Ein Geschäftsdokument erhält je nach Typ folgende Eigenschaften:

- `AccountingRelevant`
- `ImmutableAfterFinalization`
- `LegalReviewRequired`
- `AllowedParties` (B2B/B2C/Internal/Behörde/Personal)
- Verknüpfungen zu Kunde, Auftrag, Vertrag, Rechnung, Beleg und Buchung

Beispiele:

- Angebot: nicht buchungswirksam, kann zu Auftrag/Rechnung führen
- Rechnung: buchungswirksam, nach Finalisierung unveränderbar
- Mahnung: mit offener Forderung verknüpft
- Rechnungskorrektur: erzeugt Gegen-/Korrekturbuchung und verweist auf Ursprungsrechnung
- Lieferantenrechnungsbeanstandung: mit Eingangsbeleg und Kreditor verknüpft
- Verfahrensdokumentation: archiviert den GoBD-relevanten System- und Prozessstand

## UI-Navigation

Vorgesehene Hauptnavigation:

- Übersicht
- Buchhaltung
- Belege
- Rechnungen
- Geschäftsdokumente
- Kunden
- Lieferanten
- Bank
- Stripe / PayPal
- Verträge
- Mahnwesen
- Umsatzsteuer
- Monatsabschluss
- EÜR
- Anlagen
- Steuer / ELSTER
- Exporte
- Audit
- Einstellungen

## Technische Regel

Domainlogik wird nicht in WinUI-Seiten eingebaut. Die App verwendet gemeinsame Domain- und API-Modelle. Dadurch können später Plesk, API, Windows und ggf. Web-Backoffice dieselben fachlichen Regeln verwenden.
