namespace GrowCentral.Backoffice.Domain;

public sealed record DocumentSequencePolicy(string SequenceKey, string Prefix, int Padding = 6);

public static class BusinessDocumentSequenceCatalog
{
    private static readonly IReadOnlyDictionary<string, DocumentSequencePolicy> Policies =
        new Dictionary<string, DocumentSequencePolicy>(StringComparer.OrdinalIgnoreCase)
        {
            ["A1"] = new("customer-inquiry", "ANF"),
            ["A2"] = new("quote", "ANG"),
            ["A3"] = new("order-confirmation", "AB"),
            ["A4"] = new("change-order", "NA"),
            ["A5"] = new("delivery-note", "LS"),
            ["A6"] = new("service-record", "LN"),
            ["A7"] = new("acceptance-report", "AP"),
            ["B1"] = new("invoice", "RE"),
            ["B2"] = new("advance-invoice", "AR"),
            ["B3"] = new("final-invoice", "SR"),
            ["B4"] = new("invoice-correction", "RK"),
            ["B5"] = new("payment-reminder", "ZE"),
            ["B6"] = new("dunning-1", "MA1"),
            ["B7"] = new("dunning-final", "MAL"),
            ["B8"] = new("installment-agreement", "RV"),
            ["B9"] = new("balance-confirmation", "SB"),
            ["C1"] = new("complaint-ack", "REK"),
            ["C2"] = new("cure-notice", "NE"),
            ["C3"] = new("complaint-rejection", "RA"),
            ["C4"] = new("withdrawal-confirmation", "WB"),
            ["C5"] = new("withdrawal-information", "WI"),
            ["C6"] = new("termination-confirmation", "KB"),
            ["C7"] = new("extraordinary-termination", "AK"),
            ["D1"] = new("purchase-order", "BE"),
            ["D2"] = new("supplier-delay", "LV"),
            ["D3"] = new("supplier-defect", "MR"),
            ["D4"] = new("supplier-invoice-dispute", "RB"),
            ["E1"] = new("service-agreement", "DV"),
            ["E2"] = new("work-agreement", "WV"),
            ["E3"] = new("nda", "NDA"),
            ["E4"] = new("sla", "SLA"),
            ["E5"] = new("software-termination", "SK"),
            ["F1"] = new("privacy-notice", "DS"),
            ["F2"] = new("data-access", "DA"),
            ["F3"] = new("deletion-response", "DL"),
            ["F4"] = new("dpa", "AVV"),
            ["F5"] = new("data-breach", "DVF"),
            ["F6"] = new("imprint-check", "IMP"),
            ["G1"] = new("employment-agreement", "AV"),
            ["G2"] = new("vacation", "UR"),
            ["G3"] = new("employment-warning", "ABM"),
            ["G4"] = new("employment-termination", "KDG"),
            ["H1"] = new("authority-response", "FA"),
            ["H2"] = new("deadline-extension", "FV"),
            ["H3"] = new("file-note", "AKT"),
            ["H4"] = new("approval-memo", "FR"),
            ["H5"] = new("procedure-documentation", "VD")
        };

    public static DocumentSequencePolicy Get(string templateCode) =>
        Policies.TryGetValue(templateCode, out var policy)
            ? policy
            : throw new KeyNotFoundException($"Kein Nummernkreis für Dokumenttyp {templateCode} konfiguriert.");
}

public sealed record FinalDocumentOutput(
    string Subject,
    string Body,
    IReadOnlySet<string> BlockingMissingValues,
    IReadOnlySet<string> OptionalMissingValues,
    string LegalTextVersion);

public static class BusinessDocumentOutputPolicy
{
    public static FinalDocumentOutput Prepare(
        BusinessDocument document,
        (string Subject, string Body, IReadOnlySet<string> MissingValues, string LegalTextVersion) rendered)
    {
        var definition = BusinessDocumentCatalog.Get(document.TemplateCode);
        var required = definition.Fields
            .Where(x => x.Required)
            .Select(x => x.Key)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        var blocking = rendered.MissingValues.Where(required.Contains).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var optional = rendered.MissingValues.Where(x => !required.Contains(x)).ToHashSet(StringComparer.OrdinalIgnoreCase);

        var subject = rendered.Subject;
        var body = rendered.Body;
        foreach (var key in optional)
        {
            subject = subject.Replace($"[{key}]", string.Empty, StringComparison.OrdinalIgnoreCase);
            body = body.Replace($"[{key}]", string.Empty, StringComparison.OrdinalIgnoreCase);
        }

        return new(subject.Trim(), body.Trim(), blocking, optional, rendered.LegalTextVersion);
    }
}
