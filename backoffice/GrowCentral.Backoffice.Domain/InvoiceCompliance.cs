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
    bool IsExemptTransactionUnderSection4_8To29 = false,
    bool IsSmallBusinessSupplier = false,
    bool IsPassengerTicket = false);

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

        if (context.IsExemptTransactionUnderSection4_8To29)
            return new(EInvoiceRequirement.NotApplicable, "Für viele nach § 4 Nr. 8 bis 29 UStG steuerfreie Umsätze besteht keine umsatzsteuerliche Pflicht zur Ausstellung einer E-Rechnung.", "§ 14 Abs. 2 UStG");

        if (context.IsSmallAmountInvoice)
            return new(EInvoiceRequirement.NotApplicable, "Kleinbetragsrechnungen bis 250 EUR dürfen unabhängig von der allgemeinen B2B-Pflicht als sonstige Rechnung ausgestellt werden.", "§ 33 UStDV");

        if (context.IsSmallBusinessSupplier)
            return new(EInvoiceRequirement.NotApplicable, "Rechnungen von Kleinunternehmern können als sonstige Rechnung ausgestellt werden; Empfangsfähigkeit für E-Rechnungen bleibt erforderlich.", "§ 34a UStDV i. V. m. § 19 UStG");

        if (context.IsPassengerTicket)
            return new(EInvoiceRequirement.NotApplicable, "Fahrausweise, die als Rechnung gelten, können als sonstige Rechnung ausgestellt werden.", "§ 34 UStDV");

        if (context.SupplyDate < new DateOnly(2025, 1, 1))
            return new(EInvoiceRequirement.NotApplicable, "Umsatz vor Einführung der neuen E-Rechnungsregeln.", "§ 27 UStG");

        if (context.SupplyDate <= new DateOnly(2026, 12, 31))
            return new(EInvoiceRequirement.TransitionalAlternativeAllowed, "Bis 31.12.2026 darf statt einer E-Rechnung noch eine sonstige Rechnung nach der Übergangsregel verwendet werden.", "§ 27 Abs. 38 Nr. 1 UStG");

        if (context.SupplyDate <= new DateOnly(2027, 12, 31) && context.SupplierPriorYearTurnover <= 800_000m)
            return new(EInvoiceRequirement.TransitionalAlternativeAllowed, "Bei Vorjahresumsatz bis 800.000 EUR gilt die Übergangsregel bis 31.12.2027.", "§ 27 Abs. 38 Nr. 2 UStG");

        return new(EInvoiceRequirement.StructuredEInvoiceRequired, "Für den inländischen B2B-Umsatz ist nach Ablauf der einschlägigen Übergangsfrist eine strukturierte E-Rechnung erforderlich.", "§ 14 UStG i. V. m. § 27 Abs. 38 UStG");
    }
}

public static class EInvoiceStandards2026
{
    public const string XRechnungVersion = "3.0.2";
    public const string XRechnungBundle = "2026-08-31";
    public const string KositValidatorVersion = "1.6.3";
    public const string ZugferdVersion = "2.5.2";
    public const string En16931 = "EN 16931";
}
