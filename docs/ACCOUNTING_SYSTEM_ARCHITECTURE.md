# GrowCentral Accounting System Architecture

Stand: 2026-10-17

## Ziel

GrowCentral Backoffice wird zu einem vollwertigen kaufmaennischen Buchhaltungs- und Abrechnungssystem fuer den Betrieb durch eine natuerliche Einzelperson. Es muss jeden Monat einen nachvollziehbaren Abschluss liefern und die Daten fuer Umsatzsteuer, EÜR, Rechnungen, Zahlungen, Forderungen, Ausgaben, Anlagen und steuerliche Exporte konsistent fuehren.

Es ersetzt keine individuelle Steuerberatung. Steuerart, Voranmeldungszeitraum, Kleinunternehmerstatus, Ist-/Sollversteuerung und Kontenrahmen werden konfigurierbar und muessen anhand des tatsaechlichen steuerlichen Status eingerichtet werden.

## Grundsaetze

- ein zentraler Cloud-Datenbestand fuer Billing, Rechnungen, Buchungen, Belege und Entitlements;
- native Windows-App als primaere kaufmaennische Arbeitsoberflaeche;
- Plesk nur fuer Server-, Provisionierungs- und Notfalladministration;
- keine direkte PostgreSQL-Verbindung vom Windows-Client;
- jede schreibende Buchhaltungsaktion ueber versionierte Backoffice-API;
- unveraenderbare Audit-Historie fuer Buchungen, Rechnungen, Stornos, Zahlungen und Exporte;
- keine physische Loeschung gebuchter Geschaeftsvorfaelle; Korrekturen ausschliesslich durch Storno/Korrekturbuchung;
- Belegprinzip fuer jede Buchung;
- fortlaufende eindeutige Beleg- und Rechnungsnummernkreise;
- Zeitstempel, Benutzer, Quelle und Referenz fuer jede Aenderung;
- Periodensperren nach Monats-/Jahresabschluss mit explizitem Wiedereroeffnungsprozess und Audit.

## Steuerkonfiguration

Die Anwendung darf nicht annehmen, dass jeden Monat eine USt-Voranmeldung faellig ist. Intern wird jedoch immer monatlich abgeschlossen.

Konfigurierbare Steuerparameter:
- Unternehmerstatus: Regelbesteuerung / Kleinunternehmer / spaeter weitere Modi;
- USt-Voranmeldungszeitraum: Monat / Quartal / keine UStVA;
- Dauerfristverlaengerung ja/nein;
- Soll- oder Istversteuerung;
- Steuernummer;
- Umsatzsteuer-ID;
- Wirtschafts-ID;
- zustaendiges Finanzamt;
- EU-OSS Nutzung;
- Standard-USt-Saetze und Sonderfaelle;
- Geschaeftsjahr;
- EÜR als Standard-Gewinnermittlung fuer Einzelunternehmer, sofern steuerlich zutreffend.

## Buchungsengine

Doppelte Buchfuehrungslogik intern, auch wenn die steuerliche Gewinnermittlung ueber EÜR erfolgt. Dadurch bleiben Zahlungsabgleich, offene Posten, Anlagen, Umsatzsteuer und spaetere Erweiterungen konsistent.

Pflichtfelder jeder Buchung:
- booking_id
- Belegnummer
- Buchungsdatum
- Leistungs-/Belegdatum
- Konto Soll
- Konto Haben
- Nettobetrag
- Steuerbetrag
- Bruttobetrag
- Steuerkennzeichen
- Waehrung
- Gegenpartei
- Belegreferenz
- Quelle
- Ersteller
- Zeitstempel
- Storno-/Korrekturreferenz
- steuerlicher Zeitraum

Unterstuetzte Geschaeftsvorfaelle:
- Ausgangsrechnung
- Eingangsrechnung
- Gutschrift
- Storno
- Stripe-Zahlung
- PayPal-Zahlung
- SEPA-Zahlung
- Bankzahlung
- Erstattung
- Gebuehren
- freiwillige Unterstuetzung
- Hardwareverkauf
- Cloud-Abo
- Privatentnahme/-einlage
- Reisekosten und sonstige Betriebsausgaben
- Anlagegut und Abschreibung
- Steuerzahlung

## Kontenrahmen

Kontenrahmen abstrahiert konfigurieren, standardmaessig SKR03 und optional SKR04. Keine Kontonummern in Businesslogik hardcoden.

## Ausgangsrechnungen

- fortlaufende Nummernkreise;
- B2C und B2B;
- PDF-Darstellung;
- strukturierte E-Rechnung;
- XRechnung und ZUGFeRD/EN-16931 faehige Architektur;
- Rechnungskorrektur/Storno;
- Zahlungsstatus;
- Mahnstatus;
- Vertrags- und Leistungszeitraum;
- Steuerlogik pro Position;
- mehrere Steuersaetze;
- Reverse Charge und EU-Sachverhalte;
- unveraenderbare archivierte Fassung der steuerlich relevanten Rechnungsdaten.

## Eingangsrechnungen und Belege

- Upload per Windows-App;
- PDF, Bild, XML, ZUGFeRD/XRechnung;
- strukturierte E-Rechnungsdaten als Original aufbewahren;
- Belegerfassung;
- Lieferant;
- Rechnungsnummer;
- Rechnungsdatum;
- Leistungsdatum;
- Netto/USt/Brutto;
- Kontierung;
- Kostenkategorie;
- Zahlungsstatus;
- Duplikaterkennung;
- OCR nur als Hilfsmittel, Originalbeleg bleibt massgeblich.

## Zahlungsabgleich

Automatischer Abgleich von Stripe, PayPal, Bankimport und SEPA. Importierte Zahlungsprovider-Ereignisse werden nie direkt zu Buchungen umgedeutet. Ein normalisierter Payment-Ledger ordnet Provider-Transaktion, Rechnung, Gebuehr, Auszahlung, Refund und Chargeback getrennt zu.

Status:
- unmatched
- suggested
- matched
- partially_matched
- disputed
- refunded

## Bank

Phase 1: CAMT.053/MT940/CSV Import, Bankumsatz-Abgleich, offene Posten, manuelle Buchungsvorschlaege.

Phase 2: PSD2/Open-Banking-Connector ueber regulierten Drittanbieter, falls wirtschaftlich sinnvoll.

## Umsatzsteuer

Die Anwendung fuehrt ein USt-Ledger und erzeugt fuer jeden steuerlichen Zeitraum:
- steuerpflichtige Umsaetze nach Steuersatz;
- steuerfreie Umsaetze;
- innergemeinschaftliche Sachverhalte;
- Reverse-Charge-Sachverhalte;
- abziehbare Vorsteuer;
- Berichtigungen;
- Zahllast/Erstattung;
- Abgleich zur Finanzbuchhaltung;
- Plausibilitaetswarnungen;
- UStVA-Vorschau;
- XML-/ERiC-kompatible Datenaufbereitung.

Monatsabschluss erfolgt immer monatlich. Bei vierteljaehrlicher UStVA werden drei abgeschlossene Monate aggregiert.

## ELSTER / ERiC

Ziel ist direkte ELSTER-Unterstuetzung ueber ERiC, sobald GrowCentral als Steuersoftware-Hersteller/Entwickler registriert und die Hersteller-ID vorhanden ist.

Bis dahin:
- UStVA-Daten exakt nach amtlicher Feldlogik erzeugen;
- Export fuer Mein ELSTER XML, soweit das aktuelle Verfahren dies zulaesst;
- Uebertragungsprotokoll nach Abgabe archivieren;
- Abgabestatus und Transferticket speichern.

Spaetere direkte ERiC-Integration:
- Plausibilisierung;
- authentifizierte Uebermittlung;
- Transferprotokoll;
- Fehler-/Hinweisrueckgabe;
- Zertifikat niemals ungeschuetzt im Client speichern.

## EÜR und Jahresabschluss

Die Anwendung erzeugt laufende und Jahres-EÜR, Anlagen-/AfA-Verzeichnis, USt-Jahresabgleich, offene Forderungen/Verbindlichkeiten, Privatentnahmen/-einlagen, Steuerberater-Export, DATEV-kompatiblen CSV-Export als Ziel und ein Jahresarchiv mit Pruefsummen und Verfahrensdokumentation.

## Monatsabschluss

Assistent pro Monat:
1. Stripe-/PayPal-Auszahlungen importiert;
2. Bank abgeglichen;
3. offene Transaktionen markiert;
4. Eingangsbelege vollstaendig;
5. Ausgangsrechnungen vollstaendig;
6. Provider-Gebuehren verbucht;
7. Umsatzsteuer abgestimmt;
8. Anlagen/AfA gebucht;
9. Privatbuchungen geprueft;
10. Plausibilitaetspruefungen;
11. UStVA-Vorschau;
12. Monats-EÜR;
13. Abschlussbericht;
14. Periode sperren.

## GoBD-orientierte Anforderungen

- Nachvollziehbarkeit und Nachpruefbarkeit;
- Vollstaendigkeit;
- Richtigkeit;
- zeitgerechte Buchung und Aufzeichnung;
- Ordnung;
- Unveraenderbarkeit;
- maschinelle Auswertbarkeit;
- Verfahrensdokumentation;
- Datenzugriff/Export fuer Pruefung;
- Originaldaten und relevante strukturierte Datensaetze aufbewahren;
- Audit-Log unveraenderbar und exportierbar;
- keine stille Rueckdatierung oder Ueberschreibung;
- periodische Integritaetspruefungen/Hashes;
- Backup- und Restore-Nachweis.

## E-Rechnung

Unterstuetzung fuer EN 16931, XRechnung und ZUGFeRD; strukturierte Originaldaten speichern, menschenlesbar darstellen, validieren und ohne manuelles Abtippen in die Buchhaltung uebernehmen.

## Windows-App Module

Dashboard, Buchhaltung, Belege, Ausgangsrechnungen, Eingangsrechnungen, Kunden, Lieferanten, Bank, Stripe, PayPal, Vertraege, Mahnwesen, Umsatzsteuer, Monatsabschluss, EÜR, Anlagen, Provisionierung, Steuer/ELSTER, Exporte, Audit, Einstellungen.

## Sicherheit

MFA, kurze Access-Tokens, Provider-Secrets nur serverseitig, Verschluesselung sensibler Daten, signierte/hashede Abschlussarchive, Rollen fuer spaeteren Steuerberaterzugriff, Least Privilege und revisionssichere Audit-Historie.

## Verfahrensdokumentation

Die Software erzeugt und versioniert Systembeschreibung, Datenfluss, Belegerfassung, Buchungslogik, Kontenmapping, Rechtekonzept, Aenderungsprozess, Backup/Restore, Archivierung, Exportverfahren, Softwareversionen und Steuerregelversionen.

## Umsetzung

Phase A: Ledger, Kontenrahmen, Belegmodell, Audit, Rechnungsnummern, Stripe/PayPal-Normalisierung, Monatsabschluss-Grundgeruest.

Phase B: Rechnungen, Eingangsbelege, Bankimport, Reconciliation, USt-Ledger/UStVA-Vorschau, E-Rechnung.

Phase C: EÜR, Anlagenbuchhaltung, DATEV-Export, Monats-/Jahresarchive und Verfahrensdokumentation.

Phase D: ELSTER-Entwicklerregistrierung und ERiC-Integration.

## Freigabegate

Produktive Steuer-Nutzung erst nach Tests der Buchungsengine, Monatsabschluss, USt-Referenzfaelle, Rechnungsnummern, E-Rechnungsvalidierung, Export/Datenzugriff, Backup/Restore, Verfahrensdokumentation und fachlicher Pruefung des konkreten Steuer-/Kontenaufbaus.
