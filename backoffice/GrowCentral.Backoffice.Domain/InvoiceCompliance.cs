namespace GrowCentral.Backoffice.Domain;

public enum EInvoiceRequirement
{
    NotApplicable,
    TransitionalAlternativeAllowed,
    StructuredEInvoiceRequired
}

public sealed record InvoiceComplianceContext(
    DateOnly SupplyDate,
    bool SupplierEstablishedInGermany,
    bool CustomerEstablishedInGermany,
    decimal SupplierPriorYearTurnover,
    bool IsB2B,
    bool IsB2G = false,
    bool IsSmallAmountInvoice = false,
    bool IsExemptTransaction = false);

public sealed record EInvoiceDecision(EInvoiceRequirement Requirement, string Reason, string LegalReference);

public static class GermanEInvoicePolicy
{
    public static EInvoiceDecision Evaluate(InvoiceComplianceContext context)
    {
        if (!context.IsB2B)
            return new(EInvoiceRequirement.NotApplicable, "Kein inländischer B2B-Umsatz.", "§ 14 UStG");

        if (context.IsB2G)
            return new(EInvoiceRequirement.NotApplicable, "B2G wird separat nach den einschlägigen E-Rechnungsregeln des öffentlichen Auftraggebers behandelt.", "ERechV / Landesrecht");

        if (!context.SupplierEstablishedInGermany || !context.CustomerEstablishedInGermany)
            return new(EInvoiceRequirement.NotApplicable, "Die nationale Pflicht nach § 14 UStG betrifft regelmäßig Umsätze zwischen inländischen Unternehmern.", "§ 14 UStG");

        if (context.IsSmallAmountInvoice || context.IsExemptTransaction)
            return new(EInvoiceRequirement.NotApplicable, "Für den markierten Ausnahmefall wird keine allgemeine Pflicht zur strukturierten E-Rechnung erzwungen.", "§ 14 UStG / UStDV");

        if (context.SupplyDate < new DateOnly(2025, 1, 1))
            return new(EInvoiceRequirement.NotApplicable, "Umsatz vor Einführung der neuen E-Rechnungsregeln.", "§ 27 UStG");

        if (context.SupplyDate <= new DateOnly(2026, 12, 31))
            return new(EInvoiceRequirement.TransitionalAlternativeAllowed, "Bis 31.12.2026 darf statt einer E-Rechnung noch eine sonstige Rechnung nach der Übergangsregel verwendet werden.", "§ 27 Abs. 38 Nr. 1 UStG");

        if (context.SupplyDate <= new DateOnly(2027, 12, 31) && context.SupplierPriorYearTurnover <= 800_000m)
            return new(EInvoiceRequirement.TransitionalAlternativeAllowed, "Bei Vorjahresumsatz bis 800.000 EUR gilt die Übergangsregel bis 31.12.2027.", "§ 27 Abs. 38 Nr. 2 UStG");

        return new(EInvoiceRequirement.StructuredEInvoiceRequired, "Für den inländischen B2B-Umsatz ist nach Ablauf der einschlägigen Übergangsfrist eine strukturierte E-Rechnung erforderlich.", "§ 14 UStG i. V. m. § 27 Abs. 38 UStG");
    }
}
