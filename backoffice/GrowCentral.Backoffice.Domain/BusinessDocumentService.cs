using System.Globalization;

namespace GrowCentral.Backoffice.Domain;

public sealed class BusinessDocumentService
{
    private static readonly HashSet<BusinessDocumentKind> InvoiceKinds =
    [
        BusinessDocumentKind.Invoice,
        BusinessDocumentKind.AdvanceInvoice,
        BusinessDocumentKind.FinalInvoice,
        BusinessDocumentKind.InvoiceCorrection
    ];

    public ValidationResult ValidateForFinalization(BusinessDocument document, InvoiceComplianceContext? invoiceContext = null)
    {
        var template = BusinessDocumentCatalog.Get(document.TemplateCode);
        var issues = new List<ValidationIssue>();

        if (!template.AllowedParties.Contains(document.PartyType))
            issues.Add(new("party.not_allowed", $"Dokumenttyp {template.Code} ist für {document.PartyType} nicht freigegeben."));

        foreach (var field in template.Fields.Where(x => x.Required))
        {
            if (!document.Values.TryGetValue(field.Key, out var value) || string.IsNullOrWhiteSpace(value))
                issues.Add(new("field.required", $"Pflichtfeld fehlt: {field.Label} ({field.Key})."));
        }

        if (template.LegalReviewRequired && document.Status != BusinessDocumentStatus.Approved)
            issues.Add(new("legal.review_required", "Dieser Dokumenttyp erfordert vor Finalisierung eine dokumentierte fachliche/rechtliche Freigabe."));

        if (InvoiceKinds.Contains(template.Kind))
            ValidateInvoice(document, invoiceContext, issues);

        if (template.Kind is BusinessDocumentKind.FirstDunning or BusinessDocumentKind.FinalDunning)
            ValidateDunning(document, issues);

        return new(issues.All(x => !x.IsBlocking), issues);
    }

    public void Finalize(BusinessDocument document, string actor, InvoiceComplianceContext? invoiceContext = null)
    {
        var result = ValidateForFinalization(document, invoiceContext);
        if (!result.IsValid)
            throw new InvalidOperationException(string.Join(" ", result.Issues.Where(x => x.IsBlocking).Select(x => x.Message)));
        document.FinalizeDocument(actor);
    }

    public BusinessDocument CreateCorrection(BusinessDocument original, string correctionNumber, string actor, string reason)
    {
        var originalTemplate = BusinessDocumentCatalog.Get(original.TemplateCode);
        if (!originalTemplate.AccountingRelevant || original.Status is not (BusinessDocumentStatus.Finalized or BusinessDocumentStatus.Sent or BusinessDocumentStatus.Settled))
            throw new InvalidOperationException("Eine Korrektur ist nur für finalisierte buchhaltungsrelevante Dokumente vorgesehen.");

        var correction = new BusinessDocument
        {
            TemplateCode = "B4",
            Number = correctionNumber,
            PartyType = original.PartyType,
            CreatedBy = actor
        };
        correction.SetValue("party_name", original.Values.GetValueOrDefault("party_name"));
        correction.SetValue("party_address", original.Values.GetValueOrDefault("party_address"));
        correction.SetValue("document_date", DateTime.UtcNow.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        correction.SetValue("correction_number", correctionNumber);
        correction.SetValue("original_invoice_id", original.Id.ToString());
        correction.SetValue("reason", reason);
        correction.AddLink(original.Id, "corrects");
        return correction;
    }

    public void FinalizeCorrection(BusinessDocument original, BusinessDocument correction, string actor, InvoiceComplianceContext? invoiceContext = null)
    {
        if (correction.TemplateCode != "B4" || !correction.Links.Any(x => x.TargetDocumentId == original.Id && string.Equals(x.Relation, "corrects", StringComparison.OrdinalIgnoreCase)))
            throw new InvalidOperationException("Korrekturbeleg verweist nicht eindeutig auf den Ursprungsbeleg.");

        Finalize(correction, actor, invoiceContext);
        original.MarkCorrected();
    }

    private static void ValidateInvoice(BusinessDocument document, InvoiceComplianceContext? invoiceContext, ICollection<ValidationIssue> issues)
    {
        ValidateMoney(document, "gross_amount", issues);
        if (document.Values.ContainsKey("net_amount")) ValidateMoney(document, "net_amount", issues);
        if (document.Values.ContainsKey("tax_amount")) ValidateMoney(document, "tax_amount", issues);

        if (document.PartyType != PartyType.Business)
            return;

        if (invoiceContext is null)
        {
            issues.Add(new("invoice.compliance_context_missing", "Für B2B-Rechnungen müssen Leistungsdatum, Inlandsbezug, Vorjahresumsatz und Ausnahme-/B2G-Status zur E-Rechnungsprüfung vorliegen."));
            return;
        }

        var decision = GermanEInvoicePolicy.Evaluate(invoiceContext);
        document.Values.TryGetValue("e_invoice_format", out var format);
        var hasStructuredFormat = IsStructuredEInvoiceFormat(format);

        if (decision.Requirement == EInvoiceRequirement.StructuredEInvoiceRequired && !hasStructuredFormat)
            issues.Add(new("invoice.einvoice_required", $"Strukturierte E-Rechnung erforderlich: {decision.Reason} ({decision.LegalReference})."));

        if (decision.Requirement == EInvoiceRequirement.TransitionalAlternativeAllowed && !hasStructuredFormat)
            issues.Add(new("invoice.einvoice_transition", $"Übergangsregel genutzt: {decision.Reason} ({decision.LegalReference}).", IsBlocking: false));

        if (!string.IsNullOrWhiteSpace(format) && !hasStructuredFormat)
            issues.Add(new("invoice.einvoice_format_invalid", "Das angegebene strukturierte E-Rechnungsformat ist unbekannt. Zulässig im System: xrechnung, zugferd-en16931, other-en16931."));
    }

    private static void ValidateDunning(BusinessDocument document, ICollection<ValidationIssue> issues)
    {
        if (document.PartyType == PartyType.Consumer && document.Values.TryGetValue("late_fee_40_eur", out var fee) && IsTrue(fee))
            issues.Add(new("dunning.consumer_40eur_forbidden", "Die 40-EUR-Verzugspauschale darf nicht gegen Verbraucher angesetzt werden."));

        if (document.Values.TryGetValue("interest_rate_points_above_base", out var rateText) && decimal.TryParse(rateText, NumberStyles.Any, CultureInfo.InvariantCulture, out var rate))
        {
            var expected = document.PartyType == PartyType.Consumer ? 5m : 9m;
            if (rate != expected)
                issues.Add(new("dunning.interest_rate_review", $"Der eingetragene Verzugszinssatz ({rate} Prozentpunkte über Basiszins) weicht vom gesetzlichen Standardwert {expected} ab und muss begründet/geprüft werden."));
        }
    }

    private static void ValidateMoney(BusinessDocument document, string key, ICollection<ValidationIssue> issues)
    {
        if (!document.Values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value)) return;
        if (!decimal.TryParse(value, NumberStyles.Number, CultureInfo.InvariantCulture, out _))
            issues.Add(new("field.money_invalid", $"{key} ist kein gültiger Dezimalbetrag. Intern ist invariant formatierter Dezimalwert zu verwenden."));
    }

    private static bool IsStructuredEInvoiceFormat(string? format) =>
        format is not null && new[] { "xrechnung", "zugferd-en16931", "other-en16931" }.Contains(format.Trim().ToLowerInvariant());

    private static bool IsTrue(string? value) => value is not null && new[] { "1", "true", "yes", "ja" }.Contains(value.Trim().ToLowerInvariant());
}
