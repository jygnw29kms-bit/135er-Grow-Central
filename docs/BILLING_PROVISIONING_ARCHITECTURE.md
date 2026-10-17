# GrowCentral Billing & Provisioning Architecture

Stand: 2026-10-17

## Ziel

GrowCentral trennt Zahlungsabwicklung, Vertragsstatus und technische Freischaltung sauber voneinander. Das Plesk-Plugin ist die zentrale Admin-/Provisionierungsoberfläche. Kartendaten oder Bankzugangsdaten werden niemals durch das GrowCentral-Plesk-Plugin gespeichert oder verarbeitet.

## Produktmodell

- FREE: vollständiger lokaler Core, keine Cloudpflicht.
- LINK: Remotezugriff, Push/E-Mail, Offsite-Backup, Restore, 12-Monats-Cloud-Historie, Cloud-Offline-Monitoring.
- PRO: LINK plus Multi-Site, Benutzer/Rollen, Reports, Exporte, erweiterte Historie, Pro-API.
- SUPPORTER: freiwillige Unterstützung ohne Funktionsfreischaltung.

Legacy-Mapping: BASIC -> FREE, PLUS -> LINK, INTERNAL -> PRO/Test.

## Zahlungsprovider

### Primär: Stripe Billing + Checkout

Stripe übernimmt den Checkout und speichert Zahlungsdaten. GrowCentral speichert nur Provider-IDs, Status und abrechnungsrelevante Metadaten.

Ziel-Zahlungsmethoden, soweit im Händlerkonto/Land verfügbar:
- Kredit-/Debitkarte
- Apple Pay
- Google Pay
- SEPA-Lastschrift
- Stripe Link
- weitere von Stripe dynamisch angebotene lokale Zahlungsmethoden nur nach Prüfung

Verwendung:
- LINK monatlich und jährlich
- PRO monatlich und jährlich
- einmalige freiwillige Unterstützung
- optionale wiederkehrende Unterstützung getrennt vom Produkt-Abo

### Sekundär: PayPal

PayPal wird als separater Provider für Kunden angeboten, die PayPal bevorzugen. Für wiederkehrende LINK-/PRO-Abos wird die PayPal Subscriptions API verwendet. PayPal-Zustände werden in das gleiche interne Billing-Modell normalisiert.

## Architektur

Browser/PWA
  -> GrowCentral Account/Billing API
      -> Stripe Checkout / PayPal Checkout
      -> Provider verarbeitet Zahlung
      -> signierter Provider-Webhook an Billing API
      -> Billing DB aktualisieren
      -> Entitlement Service aktualisieren
      -> Pi holt signierte Entitlements über vorhandene Ed25519-Geräteidentität

Plesk Plugin
  -> interner Billing/Admin-Endpunkt
  -> Kunden, Verträge, Zahlungen, Rechnungen und Provisionierungsstatus anzeigen
  -> keine Zahlungsdaten anzeigen oder speichern
  -> Admin-Aktionen nur serverseitig und protokolliert

## Dienste

Bestehende Ports/Dienste bleiben getrennt:
- Cloud Core: 127.0.0.1:18765
- Cloud Admin/Entitlements: 127.0.0.1:18766
- Plattformstatus: 127.0.0.1:18767

Neu:
- Billing Service: vorgeschlagen 127.0.0.1:18768
- öffentlich ausschließlich über HTTPS unter z. B. /api/billing/* bzw. billing.grow-central.de
- Webhook-Endpunkte besitzen eigene Signaturprüfung und benötigen keinen Plesk-Login

## Datenmodell

billing_customers
- id
- account_id
- email
- country
- tax_status
- created_at
- updated_at

billing_provider_customers
- customer_id
- provider (stripe|paypal)
- provider_customer_id

billing_subscriptions
- id
- customer_id
- provider
- provider_subscription_id
- edition (LINK|PRO)
- interval (month|year)
- state (trialing|active|past_due|cancel_at_period_end|canceled|unpaid)
- current_period_start
- current_period_end
- cancel_at_period_end
- created_at
- updated_at

billing_payments
- id
- customer_id
- provider
- provider_payment_id
- amount_minor
- currency
- state
- paid_at
- invoice_id

billing_invoices
- id
- customer_id
- provider
- provider_invoice_id
- invoice_number
- amount_net_minor
- tax_minor
- amount_gross_minor
- currency
- state
- invoice_url/pdf reference
- created_at

billing_entitlement_links
- account_id
- device_id
- subscription_id
- edition
- provision_state

billing_webhook_events
- provider
- event_id UNIQUE
- received_at
- processed_at
- result

Idempotenz: jeder Provider-Webhook wird genau einmal logisch verarbeitet. Doppelte Events dürfen keine zweite Provisionierung auslösen.

## Provisionierungslogik

1. Benutzer besitzt GrowCentral-Cloudkonto.
2. Pi wird per bestehendem Device-Code/Ed25519-Verfahren an das Konto gekoppelt.
3. Checkout wird serverseitig für LINK oder PRO erstellt.
4. Payment Provider bestätigt den Status per signiertem Webhook.
5. Nur ein verifiziertes erfolgreiches Subscription-/Invoice-Ereignis setzt den Vertrag auf aktiv.
6. Billing Service schreibt gewünschte Edition in die zentrale Entitlement-Schicht.
7. V7 Admin liefert dem Pi die Edition über die bereits vorhandene Challenge + Ed25519-Signatur aus.
8. Bei Kündigung bleibt die Edition bis zum bezahlten Periodenende aktiv.
9. Danach fällt sie automatisch auf FREE zurück. Lokale Automationen und lokale Daten bleiben erhalten.
10. Bei Zahlungsfehler wird nicht sofort hart abgeschaltet: definierte Grace Period, danach FREE. Keine lokale Grow-Steuerung wird gesperrt.

## Plesk-Plugin: neue Bereiche

### Billing Dashboard
- MRR/ARR
- aktive LINK-Abos
- aktive PRO-Abos
- Trialing
- Past Due
- Kündigungen
- neue Zahlungen
- Umsatz Monat/Jahr
- freiwillige Unterstützungen separat

### Kunden
- Konto
- E-Mail
- Land
- Provider-Kunden-ID gekürzt/technisch
- Edition
- Zahlstatus
- verbundene Pis
- Vertragsbeginn/-ende

### Verträge
- LINK/PRO
- monatlich/jährlich
- Trial
- aktive Periode
- Kündigung zum Periodenende
- Provider
- keine manuelle Premium-Freigabe ohne Audit

### Zahlungen & Rechnungen
- Betrag
- Währung
- Provider
- Status
- Rechnungsnummer
- Beleg-/PDF-Link vom Provider
- Refund-Status

### Provisionierung
- Account -> Subscription -> Device -> Entitlement
- Soll-Edition / Ist-Edition
- letzter Entitlement-Abruf
- letzter Pi-Heartbeat
- Synchronisationsfehler
- manuelle Reparaturaktion mit Audit-Log

### Provider
- Stripe konfiguriert ja/nein
- PayPal konfiguriert ja/nein
- Webhook-Status
- letzter erfolgreicher Webhook
- Test-/Live-Modus deutlich sichtbar
- Secrets niemals im HTML ausgeben

## Öffentlicher Checkout

Der Kunde bezahlt nicht innerhalb eines selbstgebauten Kreditkartenformulars im Plesk-Panel. GrowCentral erzeugt eine serverseitige Checkout-Session und leitet zum Provider-Checkout weiter bzw. rendert dessen offizielle sichere Komponenten.

Ablauf:
- Tarif wählen
- Monat/Jahr wählen
- Preis inkl. USt. und Laufzeit sichtbar
- AGB/Datenschutz/Widerrufinformationen verlinken
- zahlungspflichtigen Button rechtskonform beschriften
- Checkout beim Provider
- Rückkehrseite zeigt nur 'Zahlung wird bestätigt'
- Edition erst nach Webhook aktivieren, niemals nur aufgrund des Browser-Redirects

## Webhooks

Stripe mindestens berücksichtigen:
- checkout.session.completed
- customer.subscription.created/updated/deleted
- invoice.paid
- invoice.payment_failed
- charge.refunded bzw. passendes Refund-Ereignis

PayPal mindestens:
- Subscription activated/updated/cancelled/suspended/expired
- relevante Payment/Capture Events

Regeln:
- Signaturprüfung zwingend
- Replay-/Event-ID-Schutz
- keine Query-String-Secrets
- vollständiges Audit ohne vollständige Zahlungsdaten
- Retry-sicher
- unbekannte Events ignorieren/loggen, nicht blind verarbeiten

## Sicherheit

- Stripe Secret Key und PayPal Secret ausschließlich serverseitig in Plesk-/Service-Secretstore bzw. root-lesbarer Environment-Konfiguration.
- Keine Keys im Git.
- Webhook-Secrets getrennt von API-Secrets.
- Provider-Test- und Live-Schlüssel strikt getrennt.
- Billing-Dienst hat keinen direkten Hardwarezugriff.
- Plesk-Plugin spricht nur localhost/interne Dienste.
- Admin-Mutationen CSRF-geschützt, Zugriff admin-only.
- Refunds, manuelle Edition-Änderungen und Vertragsänderungen auditiert.
- Keine Kartennummern, CVC, vollständige IBAN oder Wallet-Tokens in GrowCentral-Logs/DB.

## Steuern/Rechnungen

Vor Livebetrieb steuerlich festlegen:
- deutscher Unternehmerstatus/Rechtsform
- USt.-Ausweis/Kleinunternehmerstatus
- EU-B2C/OSS-Behandlung bei internationalen digitalen Leistungen
- B2B-USt-ID/Reverse-Charge falls angeboten
- Rechnungsanforderungen und fortlaufende Nummerierung
- Aufbewahrung/Export für Buchhaltung

Provider-Steuerfunktionen können unterstützen, ersetzen aber keine steuerliche Konfiguration/Beratung.

## Testbetrieb

Billing besitzt getrennten TEST-Modus:
- Stripe Testmode
- PayPal Sandbox
- keine echten Zahlungen
- Test-Pi darf FREE/LINK/PRO über das bestehende GC_EDITION_TEST_MODE simulieren
- zusätzlich End-to-End-Test: Testzahlung -> Webhook -> Entitlement -> Pi meldet richtige Edition

Produktionsmodus akzeptiert niemals lokalen Testoverride als gültige Bezahlfreischaltung.

## Umsetzungsschritte

1. Plan-Namen in Cloud V7 von BASIC/PLUS/PRO auf FREE/LINK/PRO normalisieren, Legacy-Mapping erhalten.
2. Billing Service auf Port 18768 ergänzen.
3. Stripe-Testintegration mit Checkout, Customer Portal und Webhooks.
4. Plesk-Plugin um Billing-/Kunden-/Provisionierungsansichten erweitern.
5. Entitlement-Synchronisation Billing -> V7 Admin implementieren.
6. End-to-End auf Test-Pi prüfen.
7. PayPal Sandbox als zweiter Provider ergänzen.
8. Rechnungs-/Steuerkonfiguration und Rechtsseiten finalisieren.
9. Security-/Webhook-/Refund-/Cancellation-Tests.
10. Erst danach Live-Keys hinterlegen und öffentlichen Verkauf aktivieren.
