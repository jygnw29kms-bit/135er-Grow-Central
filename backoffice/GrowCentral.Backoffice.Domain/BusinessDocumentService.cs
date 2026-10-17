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

    public ValidationResult ValidateForFinalization(BusinessDocument document)
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
            ValidateInvoice(document, issues);

        if (template.Kind is BusinessDocumentKind.FirstDunning or BusinessDocumentKind.FinalDunning)
            ValidateDunning(document, issues);

        return new(issues.All(x => !x.IsBlocking), issues);
    }

    public void Finalize(BusinessDocument document, string actor)
    {
        var result = ValidateForFinalization(document);
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
        correction.Links.Add(new(original.Id, "corrects"));
        original.MarkCorrected();
        return correction;
    }

    private static void ValidateInvoice(BusinessDocument document, ICollection<ValidationIssue> issues)
    {
        ValidateMoney(document, "gross_amount", issues);
        if (document.Values.ContainsKey("net_amount")) ValidateMoney(document, "net_amount", issues);
        if (document.Values.ContainsKey("tax_amount")) ValidateMoney(document, "tax_amount", issues);

        if (document.PartyType == PartyType.Business && document.TemplateCode == "B1")
        {
            if (!document.Values.TryGetValue("e_invoice_format", out var format) || string.IsNullOrWhiteSpace(format))
                issues.Add(new("invoice.einvoice_format_missing", "Für B2B-Ausgangsrechnungen muss das vorgesehene strukturierte E-Rechnungsformat dokumentiert werden (z. B. XRechnung oder ZUGFeRD/EN 16931)."));
            else if (!new[] { "xrechnung", "zugferd-en16931", "other-en16931" }.Contains(format.Trim().ToLowerInvariant()))
                issues.Add(new("invoice.einvoice_format_invalid", "Unbekanntes E-Rechnungsformat."));
        }
    }

    private static void ValidateDunning(BusinessDocument document, ICollection<ValidationIssue> issues)
    {
        if (document.PartyType == PartyType.Consumer && document.Values.TryGetValue("late_fee_40_eur", out var fee) && IsTrue(fee))
            issues.Add(new("dunning.consumer_40eur_forbidden", "Die 40-EUR-Verzugspauschale darf nicht gegen Verbraucher angesetzt werden."));

        if (document.Values.TryGetValue("interest_rate_points_above_base", out var rateText) && decimal.TryParse(rateText, NumberStyles.Any, CultureInfo.InvariantCulture, out var rate))
        {
            var expected = document.PartyType == PartyType.Consumer ? 5m : 9m;
            if (rate != expected)
                issues.Add(new("dunning.interest_rate_review", $"Der eingetragene Verzugszinssatz ({rate} Prozentpunkte über Basiszins) weicht vom Standardwert {expected} ab und muss begründet/geprüft werden."));
        }
    }

    private static void ValidateMoney(BusinessDocument document, string key, ICollection<ValidationIssue> issues)
    {
        if (!document.Values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value)) return;
        if (!decimal.TryParse(value, NumberStyles.Number, CultureInfo.InvariantCulture, out _))
            issues.Add(new("field.money_invalid", $"{key} ist kein gültiger Dezimalbetrag. Intern ist invariant formatierter Dezimalwert zu verwenden."));
    }

    private static bool IsTrue(string? value) => value is not null && new[] { "1", "true", "yes", "ja" }.Contains(value.Trim().ToLowerInvariant());
}
