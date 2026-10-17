# GrowCentral Accounting Legal Compliance 2026+

Stand: 2026-10-17

Diese Datei ist die technische Compliance-Baseline fuer das GrowCentral Backoffice. Sie ersetzt keine individuelle Rechts- oder Steuerberatung. Die Software muss so entworfen werden, dass gesetzliche Parameter und Fristen versioniert aktualisiert werden koennen, ohne Buchungsdaten oder historische Steuerperioden umzudeuten.

## Betreiber

GrowCentral wird aktuell durch eine natuerliche Einzelperson betrieben. Die Anwendung darf keine GmbH, UG, Gesellschaft oder sonstige nicht tatsaechlich bestehende Rechtsform unterstellen. Betreibername, Anschrift, Steuernummer, USt-ID, Wirtschafts-ID, Finanzamt, steuerlicher Status und Bankdaten werden aus einer zentralen Betreiberkonfiguration gezogen.

## 1. GoBD, aktueller Stand

Massgeblich ist die GoBD-Fassung auf Basis des BMF-Schreibens vom 28.11.2019, geaendert am 11.03.2024 und erneut am 14.07.2025. Die Aenderung 2025 beruecksichtigt insbesondere die obligatorische E-Rechnung.

Technische Muss-Regeln:
- Nachvollziehbarkeit und Nachpruefbarkeit;
- Vollstaendigkeit;
- Richtigkeit;
- zeitgerechte Aufzeichnung;
- Ordnung;
- Unveraenderbarkeit;
- maschinelle Auswertbarkeit;
- dokumentierte Verfahrensablaeufe;
- Originalformate bzw. steuerlich massgebliche strukturierte Daten aufbewahren;
- Aenderungen ausschliesslich nachvollziehbar, kein stilles Ueberschreiben;
- Storno/Korrekturbuchungen statt physischem Loeschen;
- Datenzugriff und Datenueberlassung fuer Aussenpruefungen vorbereiten;
- Export inklusive Strukturinformationen.

Das System darf niemals mit 'GoBD-zertifiziert' werben, solange keine belastbare externe Pruefung vorliegt. Die Architektur wird stattdessen als GoBD-orientiert bzw. nach den aktuellen GoBD-Anforderungen entwickelt bezeichnet.

## 2. Aufbewahrung

Nach aktuellem Recht:
- Buchungsbelege: grundsaetzlich 8 Jahre;
- Rechnungen: grundsaetzlich 8 Jahre;
- bestimmte Buecher/Aufzeichnungen nach AO weiterhin 10 Jahre;
- sonstige relevante Unterlagen je nach Kategorie 6 Jahre;
- Fristen duerfen nicht allein anhand eines Dokumenttyps pauschal geloescht werden, weil laufende Festsetzungs-/Pruefungsfristen eine laengere Vorhaltung erforderlich machen koennen.

Produktregel: Das Archiv fuehrt je Objekt `retention_class`, `retention_start`, `minimum_retention_until`, `legal_hold` und `deletion_eligible`. Automatische Loeschung steuerlicher Unterlagen ist standardmaessig deaktiviert.

## 3. E-Rechnung Deutschland

Seit 01.01.2025 muessen inlaendische Unternehmer E-Rechnungen empfangen koennen. Dies gilt auch fuer Kleinunternehmer.

Eine E-Rechnung ist seit 2025 ein strukturiertes elektronisches Format, das elektronische Verarbeitung ermoeglicht. Ein einfaches PDF ist keine E-Rechnung.

Unterstuetzte Zielstandards:
- EN 16931;
- XRechnung;
- ZUGFeRD ab Version 2.0.1, ausgenommen Profile MINIMUM und BASIC-WL;
- spaeter weitere EN-16931-konforme bzw. vereinbarte Formate mit vollstaendiger Extraktion der UStG-Pflichtangaben.

Bei hybriden Formaten ist der strukturierte Teil steuerlich fuehrend. Das System muss daher den XML-/strukturierten Datenteil als Original speichern, validieren, versionieren und visualisieren.

Uebergangsfristen fuer die Ausstellung:
- bis 31.12.2026 duerfen alle Rechnungsaussteller noch sonstige Rechnungen nutzen;
- bei Vorjahresumsatz bis 800.000 EUR verlaengert sich die Uebergangsfrist bis 31.12.2027;
- ab 01.01.2028 ist fuer betroffene inlaendische B2B-Umsaetze die E-Rechnung nach Ablauf der Uebergangsregeln verbindlich.

GrowCentral soll E-Rechnungen bereits vor dem gesetzlichen Zwang vollstaendig erstellen koennen.

## 4. Umsatzsteuer-Voranmeldung

Interner Abschluss: immer monatlich.

Gesetzlicher Voranmeldungszeitraum wird konfiguriert und darf nicht hardcodiert werden.

Aktueller § 18 UStG:
- Standard: Kalendervierteljahr;
- bei Vorjahressteuer > 9.000 EUR: Kalendermonat;
- bei Vorjahressteuer <= 2.000 EUR kann das Finanzamt von Voranmeldungen befreien;
- bei Aufnahme der gewerblichen/beruflichen Taetigkeit gelten Sonderregeln; fuer 2021 bis 2026 ist bei Aufnahme im laufenden Kalenderjahr die voraussichtliche Steuer des laufenden Jahres fuer die Einordnung massgeblich.

Die Software fuehrt daher `vat_filing_frequency` als steuerjahresbezogene Konfiguration: monthly, quarterly, exempt.

## 5. Kleinunternehmerregelung

Aktueller § 19 UStG:
- Vorjahres-Gesamtumsatz maximal 25.000 EUR;
- laufendes Kalenderjahr maximal 100.000 EUR;
- wird 100.000 EUR im laufenden Jahr ueberschritten, ist bereits der die Grenze ueberschreitende Umsatz nicht mehr von der Kleinunternehmerregelung umfasst.

GrowCentral muss beide Betriebsarten beherrschen:
- Kleinunternehmer;
- Regelbesteuerung.

Der Wechsel wird steuerjahresbezogen versioniert und darf historische Rechnungen nicht rueckwirkend veraendern.

## 6. Einzelunternehmer und Buchfuehrungspflicht

Aktuelle Schwellen nach § 141 AO fuer gewerbliche Unternehmer:
- mehr als 800.000 EUR Gesamtumsatz im Kalenderjahr oder
- mehr als 80.000 EUR Gewinn aus Gewerbebetrieb im Wirtschaftsjahr.

Nach § 241a HGB koennen Einzelkaufleute unter den dort genannten Grenzen von handelsrechtlichen Buchfuehrungs-/Inventarpflichten befreit sein.

GrowCentral fuehrt trotzdem intern eine robuste doppelte Ledger-Struktur. Die steuerliche Ausgabe kann EÜR sein, sofern dies fuer den konkreten Betreiber zulaessig ist. So muss die Engine bei spaeterer Bilanzierung nicht ersetzt werden.

## 7. EU-B2C Digitalleistungen und OSS

GC Link/Pro koennen elektronisch erbrachte Leistungen sein. Bei grenzueberschreitenden B2C-Digitalleistungen innerhalb der EU ist der Leistungsort grundsaetzlich beim Verbraucher. Eine EU-weite 10.000-EUR-Schwelle kann fuer in nur einem Mitgliedstaat ansaessige Unternehmer dazu fuehren, dass unterhalb der Schwelle die Besteuerung im Ansässigkeitsstaat verbleibt. Bei Ueberschreitung gilt die Besteuerung im Verbrauchsland; OSS kann die Meldung zentralisieren.

Das System braucht deshalb:
- Kundenland;
- B2B/B2C-Klassifizierung;
- validierte USt-ID fuer B2B, soweit relevant;
- Leistungsart;
- Belege fuer den Kundenstandort nach den jeweils geltenden EU-Regeln;
- VAT-Rate je Verbrauchsland und Leistungsdatum;
- OSS-Periode;
- OSS-Ledger getrennt von deutscher UStVA;
- Schwellenmonitor fuer 10.000 EUR;
- Option, freiwillig frueher das Verbrauchslandprinzip anzuwenden, wenn steuerlich eingerichtet.

## 8. EU-B2B

Grenzueberschreitende B2B-Dienstleistungen koennen dem Reverse-Charge-Verfahren unterliegen. Deshalb duerfen auslaendische B2B-Umsaetze nicht wie deutsche B2C-Abos behandelt werden.

Pflichtmodell:
- Land des Kunden;
- Unternehmerstatus;
- USt-ID und Validierungsnachweis;
- Reverse-Charge-Kennzeichen;
- Rechnungsvermerk;
- Zusammenfassende Meldung/weitere Meldepflichten als spaetere steuerliche Module, soweit fuer die konkrete Leistung erforderlich.

## 9. ELSTER / ERiC

ELSTER stellt ERiC als C-Bibliothek fuer Steuer-, Finanz- und Lohnbuchhaltungsprogramme bereit. Fuer die direkte Integration muss GrowCentral als Hersteller/Entwickler registriert werden; danach werden Entwicklerzugang und Hersteller-ID beantragt.

Zielarchitektur:
- amtliche Felddefinitionen versionieren;
- ERiC serverseitig oder in einem kontrollierten lokalen Steuer-Connector kapseln;
- Plausibilisierung vor Versand;
- verschluesselte Uebertragung;
- Transfer-Ticket und Rueckgabeprotokoll archivieren;
- ELSTER-Zertifikate nicht ungeschuetzt in der Windows-App speichern;
- jede Uebermittlung eindeutig mit Steuerperiode und Buchungsstand verknuepfen.

## 10. Steuerpruefung / Datenueberlassung

Die Finanzverwaltung kann maschinell auswertbare Daten und Strukturinformationen verlangen. Die GoBD enthalten einen Beschreibungsstandard fuer die Datenueberlassung, der auf den Import in Pruefsoftware wie IDEA ausgerichtet ist.

GrowCentral implementiert daher einen unveraenderbaren Pruefexport:
- Ledger;
- Konten;
- Stammdaten;
- Belege und Belegverknuepfungen;
- Steuerkennzeichen;
- Rechnungen;
- Zahlungen;
- Bankabgleich;
- Anlagen;
- Auditlog;
- Struktur-/Feldbeschreibung;
- Exportmanifest mit Hashes.

## 11. Kasse / TSE

Das reine Buchhaltungsprogramm faellt nach aktueller KassenSichV nicht als elektronisches Aufzeichnungssystem unter die TSE-Pflicht. Wenn GrowCentral spaeter jedoch ein eigenes Kassensystem/Registrierkassen-Modul fuer Barverkaeufe bekommt, ist dieses Modul gesondert nach § 146a AO/KassenSichV, TSE und DSFinV-K zu entwickeln.

Deshalb: Keine 'Kasse'-Funktion nebenbei in die Buchhaltung einbauen. Kassensystem ist ein separates Compliance-Modul.

## 12. Kommende EU-Regeln: ViDA

Das EU-Paket VAT in the Digital Age (ViDA) wurde am 11.03.2025 verabschiedet und ist seit 14.04.2025 in Kraft. Die Umsetzung erfolgt stufenweise bis 2035.

Fuer GrowCentral relevant:
- ab 01.01.2027 kleinere Aenderungen bei OSS/IOSS;
- ab 01.07.2028 Erweiterungen der Single VAT Registration und weitere Reverse-Charge-Regeln;
- ab 01.07.2030 digitale Meldepflichten fuer grenzueberschreitende B2B-Umsaetze, auf E-Rechnungen basierend;
- bis 01.01.2035 muessen bestehende nationale transaktionsbezogene Echtzeit-Meldesysteme mit dem EU-Modell harmonisiert sein.

Architekturfolge:
- Rechnungsdaten intern nie nur als PDF behandeln;
- strukturierte Invoice-Events und Tax-Events fuehren;
- jede Rechnung maschinenlesbar und revisionsfest versionieren;
- Reporting-Pipeline eventbasiert bauen;
- EU-Land, Leistungsort, Steuerkennung und Gegenpartei als strukturierte Felder fuehren;
- Meldeadapter vom Ledger entkoppeln, damit Deutschland/EU spaeter neue Meldeschemata erhalten koennen, ohne Buchungslogik umzubauen.

## 13. Deutsches E-Rechnungs-Meldesystem

Die E-Rechnung ist ausdruecklich Vorstufe eines geplanten Meldesystems. Stand Maerz 2026 weist das BMF darauf hin, dass die dafuer notwendigen gesetzlichen Aenderungen noch gesondert vorgeschlagen werden sollen.

Daher noch keine erfundene deutsche Echtzeit-Meldepflicht implementieren. Stattdessen eine generische `tax_reporting_event`-Schicht vorbereiten.

## 14. Zahlungsdaten / PCI

Kartendaten werden nicht durch GrowCentral gespeichert oder verarbeitet. Hosted Checkout/Provider-Komponenten von Stripe bzw. entsprechende PayPal-Flows bleiben die bevorzugte Architektur. GrowCentral speichert nur Provider-IDs, Status, Betrags-/Steuerdaten und Abgleichsinformationen.

## 15. Datenschutz

Buchhaltungsdaten enthalten personenbezogene Daten. Es gelten Datenminimierung, Zweckbindung, Rollen-/Rechtekonzept, Protokollierung und technische Sicherheit. Gesetzliche steuerliche Aufbewahrungspflichten haben bei steuerrelevanten Daten Vorrang vor einer sofortigen Loeschung auf Nutzerwunsch; die konkrete Rechtsgrundlage und Aufbewahrung muss dokumentiert werden.

## 16. Update- und Rechtsmonitoring

Die rechtlichen Regeln werden nicht als unveraenderlicher Programmcode modelliert.

Pflichtkomponenten:
- `legal_rule_version`;
- `tax_rule_version`;
- Gueltig-von/Gueltig-bis;
- Quelle/Rechtsgrundlage;
- Softwareversion;
- Migration ohne Rueckwirkung auf abgeschlossene Perioden;
- Warnung bei veralteter Steuerregel;
- CI-Test gegen aktuelle Schemas;
- jaehrlicher Compliance-Review mindestens vor Jahreswechsel;
- zusaetzlicher Review bei BMF-/ELSTER-/EU-Aenderungen.

Zu beobachten:
- BMF E-Rechnung und deutsches Meldesystem;
- GoBD-Aenderungen;
- ELSTER/ERiC Releases und Feldkataloge;
- UStG/AO/EStG/HGB;
- OSS/IOSS;
- ViDA 2027/2028/2030/2035;
- KassenSichV nur falls Kassensystem geplant wird;
- E-Rechnungsnorm EN 16931 und deutsche CIUS/Formatversionen.

## 17. Release-Gates

Keine produktive steuerliche Freigabe ohne:
1. aktuelle Steuerparameter fuer das jeweilige Jahr;
2. getestete USt-/EÜR-Referenzfaelle;
3. unveraenderbare Audit-/Storno-Logik;
4. E-Rechnungs-Validator;
5. 8-/10-/6-Jahres-Retention-Klassen;
6. Pruefexport;
7. Backup-/Restore-Test;
8. versionierte Verfahrensdokumentation;
9. Abstimmung des konkreten Betreiberprofils mit Steuerberater/fachkundiger Beratung;
10. dokumentierten Rechtsstand des Releases.
