using System.Text.RegularExpressions;

namespace GrowCentral.Backoffice.Domain;

public sealed record DocumentTextTemplate(string Version, string Subject, string Body, bool RequiresExternalOfficialText = false);

public static class BusinessDocumentTextCatalog
{
    public const string LegalTextVersion = "DE-2026-10-17-v1";

    public static IReadOnlyDictionary<string, DocumentTextTemplate> All { get; } = new Dictionary<string, DocumentTextTemplate>(StringComparer.OrdinalIgnoreCase)
    {
        ["A1"] = T("Ihre Anfrage vom {{request_reference}}", "{{salutation}} {{party_name}},\n\nvielen Dank für Ihre Anfrage. Gern bieten wir Ihnen auf Grundlage Ihrer Angaben folgende Lösung an:\n\n{{response}}\n\nFür eine verbindliche Kalkulation benötigen wir gegebenenfalls noch die im Vorgang gekennzeichneten Angaben. Anschließend erhalten Sie unser Angebot mit Leistungsumfang, Preis, Ausführungszeit und Zahlungsbedingungen.\n\nMit freundlichen Grüßen\n{{operator_name}}"),
        ["A2"] = T("Angebot {{offer_number}}", "ANGEBOT {{offer_number}}\n\nLeistungsumfang:\n{{scope}}\n\nNetto: {{net_amount}} EUR\nUmsatzsteuer: {{tax_amount}} EUR\nGesamt brutto: {{gross_amount}} EUR\n\nGültig bis: {{valid_until}}.\nLieferung/Ausführung: {{delivery_date}}.\nZahlungsbedingungen: {{payment_terms}}.\n\nÄnderungen oder Zusatzleistungen bedürfen einer gesonderten Vereinbarung. Bei Verbraucherverträgen gelten zusätzlich die einschlägigen gesetzlichen Pflichtinformationen."),
        ["A3"] = T("Auftragsbestätigung {{order_number}}", "Wir bestätigen Ihren Auftrag {{order_number}} über folgende Leistungen/Waren:\n\n{{scope}}\n\nGesamtbetrag: {{gross_amount}} EUR\nLieferung/Ausführung: {{delivery_date}}\nZahlungsbedingungen: {{payment_terms}}\n\nAbweichungen gegenüber Angebot oder Bestellung: {{deviations}}."),
        ["A4"] = T("Nachtrag / Änderungsauftrag {{document_number}}", "Hauptauftrag: {{parent_document_id}}\n\nÄnderung des Leistungsumfangs:\n{{change_scope}}\n\nMehr-/Minderpreis: {{price_delta}} EUR\nAuswirkung auf Termine: {{schedule_impact}}\n\nIm Übrigen bleiben die bestehenden Vereinbarungen unverändert."),
        ["A5"] = T("Lieferschein {{delivery_note_number}}", "LIEFERSCHEIN {{delivery_note_number}}\nLieferdatum: {{delivery_date}}\n\nPositionen:\n{{items}}\n\nHinweise: {{notes}}"),
        ["A6"] = T("Leistungsnachweis {{document_number}}", "Auftrag: {{order_reference}}\nLeistungszeitraum: {{service_period}}\n\nErbrachte Leistungen:\n{{services}}\n\nMaterial/Fremdleistungen: {{materials}}\nBesondere Hinweise: {{notes}}"),
        ["A7"] = T("Abnahmeprotokoll {{order_reference}}", "Abgenommener Leistungsumfang:\n{{acceptance_scope}}\n\nAbnahmestatus: {{acceptance_status}}\nFestgestellte Mängel/Restleistungen: {{defects}}\nFrist zur Erledigung: {{defect_deadline}}\nVorbehalte: {{reservations}}"),

        ["B1"] = T("Rechnung {{invoice_number}}", "RECHNUNG {{invoice_number}}\nRechnungsdatum: {{document_date}}\nLeistungsdatum/-zeitraum: {{service_date}}\n\n{{items}}\n\nNetto: {{net_amount}} EUR\nUmsatzsteuer: {{tax_amount}} EUR\nGesamt brutto: {{gross_amount}} EUR\n\nSteuernummer/USt-IdNr.: {{seller_tax_id}}\nZahlbar bis {{due_date}} ohne Abzug.\nBankverbindung: {{bank_details}}\nVerwendungszweck: {{invoice_number}}"),
        ["B2"] = T("Abschlagsrechnung {{invoice_number}}", "ABSCHLAGSRECHNUNG {{invoice_number}}\nAuftrag: {{order_reference}}\nLeistungsstand: {{service_state}}\n\nAbschlag brutto: {{gross_amount}} EUR\nZahlbar bis: {{due_date}}.\n\nDer Abschlag wird in der Schlussrechnung auf die Gesamtvergütung angerechnet."),
        ["B3"] = T("Schlussrechnung {{invoice_number}}", "SCHLUSSRECHNUNG {{invoice_number}}\nAuftrag: {{order_reference}}\n\nGesamt brutto: {{gross_amount}} EUR\nBereits berechnete/vereinnahmte Abschläge:\n{{advance_payments}}\n\nVerbleibender Zahlbetrag: {{amount_due}} EUR\nZahlbar bis: {{due_date}}."),
        ["B4"] = T("Rechnungskorrektur {{correction_number}}", "RECHNUNGSKORREKTUR / STORNO {{correction_number}}\nBezug auf Ursprungsrechnung: {{original_invoice_id}}\n\nGrund: {{reason}}\nKorrekturbetrag brutto: {{gross_amount}} EUR\n\nDer Ursprungsbeleg bleibt aus Nachweisgründen erhalten und wird durch diesen Korrekturbeleg referenziert."),
        ["B5"] = T("Zahlungserinnerung zu Rechnung {{invoice_id}}", "{{salutation}} {{party_name}},\n\nbei unserer Abstimmung ist aufgefallen, dass zu Rechnung {{invoice_id}} noch {{open_amount}} EUR offen sind. Bitte überweisen Sie den Betrag bis {{new_due_date}}.\n\nSollte sich Ihre Zahlung mit diesem Schreiben überschnitten haben, betrachten Sie die Erinnerung bitte als erledigt."),
        ["B6"] = T("1. Mahnung zu Rechnung {{invoice_id}}", "Die Forderung aus Rechnung {{invoice_id}} über {{open_amount}} EUR ist fällig. Wir fordern Sie auf, den offenen Betrag bis spätestens {{deadline}} zu überweisen.\n\nNach Eintritt des Verzugs behalten wir uns die Geltendmachung gesetzlicher Verzugszinsen und weiterer nachweisbarer Verzugsschäden vor."),
        ["B7"] = T("Letzte Mahnung zu Rechnung {{invoice_id}}", "Trotz Fälligkeit ist die Forderung weiterhin offen.\n\nHauptforderung: {{principal}} EUR\nVerzugszinsen: {{interest}} EUR\nSonstige erstattungsfähige Verzugskosten: {{costs}} EUR\n\nWir setzen letztmalig eine Zahlungsfrist bis {{deadline}}. Nach fruchtlosem Ablauf behalten wir uns die Einleitung des gerichtlichen Mahn- oder Klageverfahrens vor."),
        ["B8"] = T("Ratenzahlungsvereinbarung", "Forderung: {{claim_reference}}\nGesamtstand: {{total_amount}} EUR\n\nVereinbarter Ratenplan:\n{{installment_plan}}\n\nZahlungen werden nach den gesetzlichen Regeln verrechnet. Im Übrigen bleibt die Forderung bestehen, soweit nicht ausdrücklich etwas anderes vereinbart ist."),
        ["B9"] = T("Saldenbestätigung zum {{balance_date}}", "Nach unseren Unterlagen besteht zum {{balance_date}} ein Saldo von {{balance}} EUR.\n\nOffene Belege:\n{{open_items}}\n\nBitte bestätigen Sie den Saldo oder teilen Sie Abweichungen mit Belegreferenz mit."),

        ["C1"] = T("Ihre Reklamation zu {{claim_reference}}", "Wir bestätigen den Eingang Ihrer Reklamation. Sie schildern folgenden Mangel:\n\n{{complaint}}\n\nWir prüfen den Vorgang anhand der Vertrags- und Leistungsunterlagen. Diese Eingangsbestätigung enthält noch kein Anerkenntnis einer Rechtspflicht oder eines bestimmten Mangels."),
        ["C2"] = T("Nacherfüllung zu {{claim_reference}}", "Wir erkennen folgenden Mangel zur Nacherfüllung an:\n{{accepted_defect}}\n\nDie Nacherfüllung erfolgt durch {{remedy}}. Vorgesehener Termin: {{deadline}}. Weitergehende Rechte richten sich nach den gesetzlichen Voraussetzungen und dem konkreten Vertragsverhältnis."),
        ["C3"] = T("Prüfergebnis Ihrer Reklamation {{claim_reference}}", "Wir haben Ihre Reklamation geprüft. Nach dem derzeit dokumentierten Sachverhalt können wir die geltend gemachten Mängelansprüche aus folgenden Gründen nicht anerkennen:\n\n{{findings}}\n{{reason}}\n\nNeue erhebliche Unterlagen oder Tatsachen prüfen wir erneut. Diese Erklärung beruht auf dem derzeit dokumentierten Sachstand."),
        ["C4"] = T("Bestätigung Ihres Widerrufs {{contract_reference}}", "Wir bestätigen den Eingang Ihres Widerrufs vom {{withdrawal_received}} zum Vertrag/Auftrag {{contract_reference}}.\n\nDie Rückabwicklung erfolgt nach den gesetzlichen Vorgaben:\n{{return_process}}\n\nEin etwaiger Wertersatz wird nur verlangt, soweit die gesetzlichen Voraussetzungen erfüllt sind."),
        ["C5"] = new(LegalTextVersion, "Widerrufsbelehrung", "Für diesen Dokumenttyp muss das jeweils einschlägige amtliche Muster nach Anlage 1 zu Art. 246a EGBGB mit den konkreten Vertragsdaten erzeugt werden. Die Anwendung darf an dieser Stelle keine frei formulierte Ersatzbelehrung verwenden. Das gesetzliche Muster-Widerrufsformular ist zusätzlich bereitzustellen.", true),
        ["C6"] = T("Kündigungsbestätigung {{contract_reference}}", "Wir bestätigen den Eingang Ihrer Kündigung zum Vertrag {{contract_reference}}. Das Vertragsverhältnis endet nach den maßgeblichen Bedingungen zum {{termination_date}}. Bis dahin werden vereinbarte Leistungen und Entgelte vertragsgemäß fortgeführt. Offene Forderungen bleiben unberührt."),
        ["C7"] = T("Außerordentliche Vertragsbeendigung {{contract_reference}}", "Hiermit erklären wir die außerordentliche Vertragsbeendigung zum {{effective_date}} aufgrund folgenden Sachverhalts:\n\n{{reason}}\n\nVorherige Abmahnung/Fristsetzung bzw. deren Entbehrlichkeit: {{prior_notice}}\n\nRechte wegen offener Forderungen und sonstiger Ansprüche bleiben vorbehalten."),

        ["D1"] = T("Bestellung {{purchase_order_number}}", "BESTELLUNG {{purchase_order_number}}\n\n{{items}}\n\nGesamtbetrag: {{gross_amount}} EUR\nGewünschter Liefertermin: {{requested_delivery}}\nZahlungsbedingungen: {{payment_terms}}\n\nBitte bestätigen Sie Bestellung, Preis und Liefertermin in Textform."),
        ["D2"] = T("Nachfrist zu Bestellung {{purchase_order_reference}}", "Der vereinbarte Liefertermin {{original_delivery_date}} ist verstrichen; die Leistung ist noch nicht vollständig eingegangen. Wir fordern Sie auf, die ausstehende Leistung bis spätestens {{deadline}} vollständig zu erbringen. Nach fruchtlosem Fristablauf behalten wir uns die gesetzlichen und vertraglichen Rechte vor."),
        ["D3"] = T("Mängelrüge zu Lieferung {{delivery_reference}}", "Lieferung eingegangen am {{delivery_date}}.\n\nFestgestellter Mangel:\n{{defect}}\n\nWir verlangen Nacherfüllung durch {{requested_remedy}}. Bitte teilen Sie uns das weitere Vorgehen einschließlich Rücktransport/Abholung mit. Weitere Rechte bleiben vorbehalten."),
        ["D4"] = T("Beanstandung Lieferantenrechnung {{supplier_invoice_number}}", "Wir können die Rechnung derzeit nicht zur Zahlung freigeben.\n\nGrund: {{reason}}\nUnstreitiger Betrag: {{undisputed_amount}} EUR\n\nBitte senden Sie eine nachvollziehbare Korrektur bzw. berichtigte Rechnung mit Bezug auf den Ursprungsbeleg."),

        ["E1"] = T("Dienstleistungsvertrag", "Vertragsparteien: {{party_name}} / {{operator_name}}\n\n1. Leistung: {{scope}}\n2. Laufzeit: {{term}}\n3. Vergütung: {{compensation}}\n4. Mitwirkungspflichten: {{cooperation}}\n5. Nutzungsrechte: {{rights}}\n6. Vertraulichkeit/Datenschutz: {{privacy}}\n7. Haftung: Es gelten die gesetzlichen Regelungen, soweit keine wirksame abweichende Vereinbarung getroffen ist.\n8. Änderungen werden aus Beweisgründen in Textform dokumentiert; zwingendes Recht bleibt unberührt."),
        ["E2"] = T("Werk-/Projektvertrag", "1. Geschuldetes Werk/Spezifikation: {{work_specification}}\n2. Meilensteine: {{milestones}}\n3. Mitwirkung Auftraggeber: {{cooperation}}\n4. Vergütung: {{compensation}}\n5. Änderungen erfolgen über bestätigte Nachträge.\n6. Abnahme: {{acceptance}}\n7. Nutzungsrechte: {{rights}}\n8. Mängelrechte, Datenschutz und Vertragsbeendigung richten sich nach Vertrag und Gesetz."),
        ["E3"] = T("Vertraulichkeitsvereinbarung", "Zweck: {{purpose}}\n\nAls vertraulich gelten die im Rahmen des Zwecks offengelegten, als vertraulich gekennzeichneten oder ihrer Natur nach erkennbar vertraulichen Informationen: {{confidential_scope}}. Die Informationen dürfen nur zweckgebunden und nur befugten Personen zugänglich gemacht werden. Gesetzliche Offenlegungspflichten bleiben unberührt.\n\nDauer: {{duration}}. Geschäftsgeheimnisse sind darüber hinaus solange zu schützen, wie die gesetzlichen Schutzvoraussetzungen bestehen."),
        ["E4"] = T("Service Level Agreement {{service}}", "Dienst: {{service}}\nVerfügbarkeit: {{availability}}\nSupportzeiten: {{support_times}}\nPrioritäten/Reaktionsziele:\n{{priority_targets}}\n\nMessmethode: {{measurement}}\nWartungsfenster: {{maintenance}}\nAusnahmen: {{exceptions}}"),
        ["E5"] = T("Kündigungsbestätigung {{contract_reference}}", "Vertragsende: {{access_until}}\nDatenexport möglich bis: {{export_until}}\nLöschung/weitere Speicherung: {{deletion_policy}}\n\nBitte sichern oder exportieren Sie benötigte Daten vor dem genannten Termin. Gesetzliche Aufbewahrungspflichten bleiben unberührt."),

        ["F1"] = T("Datenschutzhinweise", "Verantwortlicher: {{controller}}\n\nZwecke und Rechtsgrundlagen:\n{{purposes}}\n\nEmpfänger/Kategorien: {{recipients}}\nDrittlandübermittlungen: {{third_country}}\nSpeicherdauer: {{retention}}\nBetroffenenrechte: {{rights}}\nBereitstellungspflicht/Folgen: {{provision_requirement}}\nAutomatisierte Entscheidungen/Profiling: {{profiling}}"),
        ["F2"] = T("Eingang Ihres Auskunftsersuchens", "Wir bestätigen den Eingang Ihres Auskunftsersuchens vom {{request_received}}. Wir prüfen die Ihrer Person zugeordneten Daten und, soweit erforderlich, die sichere Identifizierung. Die Bearbeitung erfolgt innerhalb der gesetzlichen Frist. Identitätsprüfung: {{identity_check}}"),
        ["F3"] = T("Antwort auf Ihr Löschersuchen", "Wir haben Ihr Löschersuchen vom {{request_received}} geprüft.\n\nGelöscht bzw. zur Löschung vorgemerkt: {{deleted_categories}}\nWeiter gespeichert: {{retained_categories}}\nRechts-/Speichergrund: {{retention_reason}}\n\nWeiter gespeicherte Daten werden nur im rechtlich zulässigen Umfang verarbeitet und nach Wegfall des Speichergrundes gelöscht."),
        ["F4"] = T("Vereinbarung zur Auftragsverarbeitung", "Verantwortlicher: {{controller}}\nAuftragsverarbeiter: {{processor}}\n\nGegenstand, Art und Zweck: {{processing_scope}}\nBetroffene Personen: {{data_subjects}}\nDatenarten: {{data_types}}\nTechnische und organisatorische Maßnahmen: {{toms}}\nUnterauftragsverarbeiter: {{subprocessors}}\n\nWeisungsbindung, Vertraulichkeit, Unterstützungspflichten, Vorfallmeldung, Löschung/Rückgabe, Nachweise/Audits und Drittlandtransfers richten sich nach Art. 28 DSGVO und den konkret vereinbarten Anlagen."),
        ["F5"] = T("Interne Erstmeldung Datenschutzvorfall", "Entdeckt am: {{discovered_at}}\nVorfall: {{incident}}\nDatenkategorien: {{data_categories}}\nBetroffene: {{affected_people}}\nMögliche Folgen/Risiko: {{risk}}\nSofortmaßnahmen: {{immediate_actions}}\n\nMeldepflicht nach Art. 33 DSGVO: {{authority_notification}}\nBenachrichtigung nach Art. 34 DSGVO: {{subject_notification}}\nEntscheidung und Begründung sind zu dokumentieren; die 72-Stunden-Frist ist zu überwachen."),
        ["F6"] = T("Impressumsprüfung {{service_url}}", "Dienst: {{service_url}}\nAnbieterangaben: {{provider_data}}\nKontakt: {{contact}}\nRegister/Aufsicht/Steuer- und Berufsangaben soweit einschlägig: {{additional_provider_data}}\n\nPrüfergebnis: {{review_result}}"),

        ["G1"] = T("Arbeitsvertrag", "Arbeitnehmer: {{employee_name}}\nBeginn: {{start_date}}\nArbeitsort: {{workplace}}\nTätigkeit: {{role}}\nVergütung: {{salary}}\nArbeitszeit: {{working_time}}\nUrlaub: {{vacation}}\nProbezeit/Befristung: {{probation_term}}\nKündigungsregelungen: {{termination_rules}}\nWeitere wesentliche Arbeitsbedingungen: {{additional_terms}}"),
        ["G2"] = T("Urlaubsantrag {{employee_name}}", "Beantragter Urlaub: {{vacation_from}} bis {{vacation_to}}\nArbeitstage: {{work_days}}\nVertretung/Übergabe: {{handover}}\nEntscheidung: {{decision}}\nBegründung bei Ablehnung: {{decision_reason}}"),
        ["G3"] = T("Abmahnung", "{{salutation}} {{employee_name}},\n\nam {{incident_at}} haben Sie nach unserer Feststellung folgende konkrete arbeitsvertragliche Pflicht verletzt:\n{{facts}}\n\nBetroffene Pflicht: {{duty}}. Wir fordern Sie auf, dieses Verhalten künftig zu unterlassen und Ihre arbeitsvertraglichen Pflichten ordnungsgemäß zu erfüllen. Bei einer erneuten vergleichbaren Pflichtverletzung müssen Sie mit weiteren arbeitsrechtlichen Konsequenzen bis hin zur Kündigung rechnen."),
        ["G4"] = T("Kündigung des Arbeitsverhältnisses", "{{salutation}} {{employee_name}},\n\nhiermit kündigen wir das bestehende Arbeitsverhältnis ordentlich zum {{termination_date}}, hilfsweise zum nächstzulässigen Termin.\n\nRückgabe betrieblicher Gegenstände/Zugänge: {{return_items}}\nUrlaub/Zeitguthaben: {{time_balance}}\n\nDie gesetzlich erforderliche Schriftform und eigenhändige Unterschrift sind einzuhalten."),

        ["H1"] = T("Ihr Schreiben / Aktenzeichen {{reference}}", "Sehr geehrte Damen und Herren,\n\nzu Ihrem Schreiben nehmen wir wie folgt Stellung:\n\n{{response}}\n\nSteuernummer: {{tax_number}}\nAnlagen/Nachweise: {{attachments}}\n\nMit freundlichen Grüßen\n{{operator_name}}"),
        ["H2"] = T("Antrag auf Fristverlängerung {{reference}}", "Die gesetzte Frist endet am {{current_deadline}}. Aus folgendem Grund ist eine vollständige Bearbeitung bis dahin nicht möglich:\n{{reason}}\n\nWir beantragen daher eine Fristverlängerung bis {{requested_deadline}} und bitten um Bestätigung."),
        ["H3"] = T("Aktennotiz {{subject}}", "Datum/Uhrzeit: {{occurred_at}}\nBeteiligte: {{participants}}\nThema: {{subject}}\n\nWesentliche Tatsachen/Aussagen:\n{{facts}}\n\nVereinbarte Maßnahmen: {{actions}}\nFristen/Verantwortliche: {{deadlines}}"),
        ["H4"] = T("Freigabevermerk {{reference}}", "Vorgang: {{reference}}\nGeprüft wurden: {{checks}}\nEntscheidung: {{decision}}\nBegründung/Auflagen: {{conditions}}\nFreigabe durch: {{approved_by}}\nFreigabezeitpunkt: {{approved_at}}"),
        ["H5"] = T("Verfahrensdokumentation Buchhaltung/Belegwesen", "Systeme/Versionen: {{systems}}\nBelegeingang: {{incoming_documents}}\nPrüfung/Freigabe: {{approval_process}}\nBuchungsprozess: {{posting_process}}\nRechnungsausgang/Korrekturen: {{outgoing_documents}}\nArchivierung/Originalformate: {{archiving}}\nBackup/Restore: {{backup_restore}}\nBenutzer/Rechte: {{permissions}}\nÄnderungsmanagement: {{change_management}}\nDatenzugriff/Export: {{tax_audit_export}}")
    };

    private static DocumentTextTemplate T(string subject, string body) => new(LegalTextVersion, subject, body);
}

public sealed class BusinessDocumentRenderer
{
    private static readonly Regex Placeholder = new("\\{\\{(?<key>[a-zA-Z0-9_]+)\\}\\}", RegexOptions.Compiled);

    public (string Subject, string Body, IReadOnlySet<string> MissingValues, string LegalTextVersion) Render(BusinessDocument document, IReadOnlyDictionary<string, string?>? globalValues = null)
    {
        if (!BusinessDocumentTextCatalog.All.TryGetValue(document.TemplateCode, out var text))
            throw new KeyNotFoundException($"Kein Textmaster für {document.TemplateCode} vorhanden.");

        var values = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
        if (globalValues is not null)
            foreach (var pair in globalValues) values[pair.Key] = pair.Value;
        foreach (var pair in document.Values) values[pair.Key] = pair.Value;
        values["document_number"] = document.Number;

        var missing = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        string Apply(string input) => Placeholder.Replace(input, match =>
        {
            var key = match.Groups["key"].Value;
            if (values.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value)) return value!;
            missing.Add(key);
            return $"[{key}]";
        });

        return (Apply(text.Subject), Apply(text.Body), missing, text.Version);
    }
}
