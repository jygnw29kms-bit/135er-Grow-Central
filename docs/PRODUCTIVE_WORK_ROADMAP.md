# GrowCentral Produktive Arbeits-Roadmap

Stand: 2026-10-17

## Ziel
GrowCentral wird in einer festen, abhängigkeitssicheren Reihenfolge weiterentwickelt. Priorität hat produktive Fertigstellung statt paralleler Teilbaustellen.

## Phase A — Pi, First-Boot, GUI, i18n
1. Test-Pi wieder über den vorgesehenen Wartungszugang deploybar machen.
2. First-Boot vollständig stabilisieren: Sprache zuerst, Locale persistent, Netzwerk, lokaler Login, optionaler Cloud-Login, Recovery.
3. GUI auf Final-Master-Niveau bringen: futuristisches Hero-Control-Center, funktionale SVGs, responsive PWA, keine AI-Optik.
4. Bestehende UI vollständig auf i18n migrieren, mindestens DE/EN, keine neuen Hardcodes.
5. Kernbereiche live verdrahten: Dashboard, Räume/Zonen, Geräte, Sensoren, Automationen, Energie, Kamera, Historie, HomeKit/Home Assistant, Diagnose.

## Phase B — FREE / LINK / PRO
1. Capability-Matrix vereinheitlichen.
2. FREE behält sämtliche lokalen Kernfunktionen.
3. LINK erweitert Remote, Push/E-Mail, Offsite-Backup, Restore, Cloud-Historie und Offline-Monitoring.
4. PRO erweitert Multi-Site, RBAC, Audit, Reports, Exporte, längere Historie und Pro-API.
5. Test-Pi muss FREE/LINK/PRO simulieren können.
6. Abo-Ende oder Cloud-Ausfall darf lokale Grow-Steuerung niemals deaktivieren.

## Phase C — Cloud, Billing, Provisionierung
1. internen Billing-Service implementieren.
2. zentrale Datenmodelle für Kunden, Verträge, Zahlungen, Rechnungen, Webhooks, Provisionierung und Entitlements.
3. Stripe zunächst im Test Mode anbinden.
4. danach PayPal Sandbox.
5. Webhooks sind alleinige Autorität für Zahlungsstatus; Browser-Redirects schalten niemals Premium frei.
6. Provisionierung muss idempotent und auditierbar sein.

## Phase D — Plesk Modul
Plesk bleibt Server- und Fallback-Verwaltung für:
- Cloud-/Dienststatus
- Kunden und Verträge
- Zahlungen und Rechnungen
- FREE/LINK/PRO
- Geräte und Provisionierung Soll/Ist
- Webhookstatus
- Stripe/PayPal-Status
- Supporter
- Diagnose und Systemzustand

## Phase E — Native Windows Backoffice
Technik: C# + WinUI 3 + Windows App SDK.
Die App nutzt dieselbe Cloud-/Billing-/Backoffice-API wie Plesk und führt keine zweite Datenbank.

Bereiche:
- Dashboard: Umsatz, MRR, ARR, offene Forderungen, Steuer, Supporter
- Kunden
- Verträge und Kündigungen
- Zahlungen, Refunds, Chargebacks
- Rechnungen und E-Rechnungen
- Provisionierung
- Geräte
- Audit
- Buchhaltung und Steuer

## Phase F — Vollwertige Finanzbuchhaltung
1. doppelte Ledger-Struktur intern.
2. Journal, Kontenplan, Buchungssätze, Belegnummern und Perioden.
3. Unveränderbarkeit und Storno statt Löschen.
4. Eingangs- und Ausgangsbelege.
5. Bank- und Provider-Abgleich.
6. USt-/Vorsteuer-Ledger.
7. Monatsabschluss unabhängig vom tatsächlichen Voranmeldungszeitraum.
8. EÜR-Ausgabe, solange steuerlich zulässig.
9. Anlagenverwaltung und AfA.
10. E-Rechnung: XRechnung/ZUGFeRD mit Erhalt des strukturierten Originals.
11. GoBD-Prüfexport und Verfahrensdokumentation.
12. ELSTER/ERiC später direkt integrieren.
13. OSS und EU-B2C-Digitalleistungen berücksichtigen.
14. Regelstände versionieren, damit abgeschlossene Perioden ihren damaligen Rechtsstand behalten.

## Phase G — Recht und Compliance
Pflegen und versionieren:
- AGB
- Datenschutz
- Widerruf
- Kündigung
- Impressum
- OSS-Lizenzen
- Security Policy
- Update Policy
- Support Policy
- Verfahrensdokumentation
- GoBD
- E-Rechnung
- USt/OSS
- ViDA
- CRA
- DSGVO
- ELSTER/ERiC
- Aufbewahrungsfristen

## Phase H — Freiwillige Unterstützung
Free bleibt vollständig Free.
Unterstützung wird als freiwillige Förderung/Sponsoring behandelt und technisch von LINK/PRO getrennt.
Keine Premium-Funktion allein aufgrund einer Unterstützung.

## Phase I — Hardware
Erst nach stabilem Softwarekern:
- Raspberry Pi
- Originalnetzteil
- SD-Karte
- Gehäuse
- ESP32/Seeed/Waveshare
- Sensoren/Kabel
- dokumentierte DIY-Bundles
Keine selbstgebauten 230-V-Produkte in Phase 1.

## Harte Fertig-Kriterien
Ein Bereich gilt erst als fertig, wenn:
- Code im Master ist
- Tests vorhanden sind
- echte UI verdrahtet ist
- keine Mockdaten nötig sind
- Fehler- und Offlinezustände behandelt werden
- DE/EN vollständig sind
- Security-Gates bestanden sind
- Dokumentation vorhanden ist
- reale Zielhardware bzw. reale Provider-Sandbox getestet wurde

## Aktueller Fokus
1. Test-Pi wieder deploybar machen.
2. FREE/LINK/PRO real testen.
3. GUI/i18n fertig migrieren.
4. Billing-Service implementieren.
5. Plesk-Provisionierung anschließen.
6. Windows-Backoffice starten.
7. Buchhaltungsledger und E-Rechnung aufbauen.

## Betreiberstruktur
GrowCentral wird aktuell von einer einzelnen natürlichen Person betrieben. Projekt-, Vertrags-, Rechnungs-, Datenschutz- und Steuertexte dürfen keine nicht existente Gesellschaft oder Teamstruktur vortäuschen. Betreiberangaben werden zentral konfiguriert, damit eine spätere Rechtsformänderung ohne Datenmodellbruch möglich bleibt.
