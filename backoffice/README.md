# GrowCentral Vertragsabrechnung / Backoffice

## Verbindlicher Zweck

Das GrowCentral-Backoffice ist **keine allgemeine Unternehmensbuchhaltung** und kein ERP für beliebige Geschäftsprozesse. Es dient ausschließlich der kaufmännischen Abwicklung der **GrowCentral-Verträge** und der daraus entstehenden Forderungen, Rechnungen und Zahlungen.

Der Betreiber ist als **Einzelunternehmen / sole proprietor** modelliert. Es gibt keine Aktiengesellschaft, keine Konzernstruktur, keine Gesellschafter-/Aktienverwaltung und keine dafür typischen Rechnungslegungsfunktionen.

## Verbindliche Prozesskette

`Kunde -> GrowCentral-Vertrag -> Abrechnungsperiode/Leistung -> Rechnung -> Zahlung -> ggf. Mahnung/Korrektur -> steuerliche Auswertung`

Jede buchungsrelevante Bewegung muss auf einen GrowCentral-Vertrag, eine daraus erzeugte Rechnung oder deren Zahlung/Korrektur zurückführbar sein. Freie allgemeine Unternehmensbuchungen außerhalb dieses Zusammenhangs gehören nicht zum Produktumfang.

## Module

1. **Übersicht**
   - aktive GrowCentral-Verträge
   - nächste Abrechnungen
   - Umsatz aus GrowCentral-Verträgen
   - offene Forderungen
   - eingegangene Zahlungen
   - überfällige Rechnungen / Mahnungen
   - Providergebühren, soweit sie unmittelbar einer GC-Zahlung zugeordnet sind

2. **Kunden**
   - Rechnungs- und Kontaktdaten
   - B2B/B2C-Kennzeichnung
   - USt-ID soweit erforderlich
   - zugehörige GrowCentral-Verträge
   - Rechnungs- und Zahlungshistorie

3. **GrowCentral-Verträge**
   - Vertragsnummer
   - Kunde
   - Produkt/Tarif
   - Beginn, Laufzeit, Kündigung
   - Abrechnungsintervall
   - Preis und Steuerbehandlung
   - Zahlungsart
   - Status
   - Vertragsänderungen mit Historie
   - Grundlage jeder Abrechnung

4. **Abrechnung / Rechnungen**
   - periodische und einmalige Vertragsabrechnung
   - Rechnung, Abschlag soweit vertraglich nötig, Korrektur/Storno
   - EN 16931 / XRechnung / ZUGFeRD soweit gesetzlich erforderlich
   - unveränderbare Finalfassung
   - eindeutige Nummernkreise
   - Verknüpfung mit Vertrag und Abrechnungsperiode

5. **Zahlungen**
   - Zahlungseingänge zu GC-Rechnungen
   - Stripe/PayPal/Bank nur als Zahlungsquellen der Vertragsabrechnung
   - Gebühren und Refunds nur soweit sie einer GC-Zahlung zugeordnet sind
   - automatische bzw. manuelle Zuordnung zur Rechnung
   - keine allgemeine Bankbuchhaltung

6. **Mahnwesen**
   - Zahlungserinnerung
   - Mahnstufen
   - Verzugszinsen und B2B/B2C-Regeln
   - keine 40-EUR-Pauschale gegen Verbraucher
   - Bezug immer auf eine offene GrowCentral-Rechnung

7. **Steuerliche Auswertung der GC-Abrechnung**
   - Umsatzsteuer aus GrowCentral-Rechnungen
   - vereinnahmte/vereinbarte Steuer entsprechend konfiguriertem Steuerstatus
   - Korrekturen und Stornos
   - Providergebühren nur soweit unmittelbar abrechnungsbezogen
   - periodische Summen als Grundlage für die steuerliche Meldung
   - keine allgemeine Kosten-, Anlagen-, Lohn- oder Lieferantenbuchhaltung

8. **Audit / Archiv**
   - Vertrag, Rechnung, Zahlung, Mahnung und Korrektur nachvollziehbar versioniert
   - finalisierte Rechnungen unveränderbar
   - Korrekturen nur über Korrektur-/Stornovorgänge
   - Hash-/Integritätsprüfung
   - gesetzlich erforderliche Aufbewahrung

9. **Einstellungen**
   - Betreiber als Einzelunternehmen
   - Geschäftsbezeichnung
   - Anschrift
   - Steuernummer / USt-ID / Wirtschafts-ID soweit vorhanden
   - Finanzamt
   - Steuerstatus
   - Ist-/Sollversteuerung
   - Nummernkreise
   - E-Rechnungsformat
   - Zahlungsprovider
   - Rollen und MFA

## Ausdrücklich nicht Bestandteil

Folgende Funktionen gehören **nicht** in die GrowCentral-Vertragsabrechnung:

- allgemeine Kreditoren-/Lieferantenbuchhaltung
- Einkaufsbestellungen und allgemeine Eingangsrechnungen
- Lager, Warenwirtschaft oder Beschaffung
- allgemeine Privatentnahmen/-einlagen-Verwaltung
- Anlagenbuchhaltung und AfA-Verwaltung als eigenes Modul
- Lohn-/Gehaltsbuchhaltung
- allgemeine Kassenbuchhaltung
- beliebige manuelle Journalbuchungen ohne GC-Vertrags-/Rechnungsbezug
- Konzern-, Beteiligungs-, Gesellschafter- oder Aktienverwaltung
- AG-spezifische Rechnungslegung, Hauptversammlung, Aktienkapital oder Dividenden
- allgemeines ERP oder DATEV-Ersatz für das gesamte Unternehmen

Wenn für die gesetzlich korrekte Abrechnung technisch Soll/Haben-Sätze oder Steuerkonten verwendet werden, bleiben diese **interne Mechanik der Vertragsabrechnung** und werden nicht zu einer frei nutzbaren Vollbuchhaltung ausgebaut.

## Eine Quelle der Wahrheit

Die Cloud ist die führende Datenquelle. Die Windows-App ist kein eigener Buchhaltungs-Master.

Verbindliche Referenzen:

`CustomerId -> ContractId -> BillingPeriodId -> InvoiceId -> PaymentId`

Korrekturen und Mahnungen referenzieren zusätzlich immer die ursprüngliche `InvoiceId`.

## UI-Navigation

Vorgesehene Hauptnavigation:

- Übersicht
- Kunden
- Verträge
- Abrechnungen
- Rechnungen
- Zahlungen
- Mahnungen
- Steuerübersicht
- Archiv / Audit
- Einstellungen

Kein Menüpunkt „Buchhaltung“ im Sinne einer universellen Finanzbuchhaltung. Die kaufmännische Logik erscheint dort, wo sie zur GC-Vertragsabrechnung gebraucht wird.

## Technische Regel

Domainlogik wird nicht in WinUI-Seiten eingebaut. Vertrag, Abrechnungsperiode, Rechnung, Zahlung und Korrektur sind die zentralen Domainobjekte. Allgemeine Ledger-Technik darf intern verwendet werden, aber nur mit zwingendem Bezug auf diese Objekte.
