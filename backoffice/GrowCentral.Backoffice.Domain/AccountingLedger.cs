namespace GrowCentral.Backoffice.Domain;

public sealed record JournalLine(
    string AccountNumber,
    decimal Debit,
    decimal Credit,
    string? TaxCode = null,
    decimal? TaxRate = null,
    decimal? TaxAmount = null,
    Guid? PartyId = null,
    Guid? DocumentId = null,
    string? Memo = null);

public sealed record JournalEntryDraft(
    DateOnly BookingDate,
    DateOnly DocumentDate,
    string Description,
    string? Reference,
    Guid? SourceDocumentId,
    IReadOnlyList<JournalLine> Lines,
    Guid? ReversalOfEntryId = null,
    Guid? ContractId = null,
    Guid? BillingPeriodId = null,
    Guid? PaymentId = null);

public sealed record LedgerValidation(IReadOnlyList<string> Errors, decimal DebitTotal, decimal CreditTotal)
{
    public bool IsValid => Errors.Count == 0;
}

public static class DoubleEntryLedgerPolicy
{
    public static LedgerValidation Validate(JournalEntryDraft entry)
    {
        var errors = new List<string>();
        if (entry.Lines.Count < 2) errors.Add("Eine Buchung benötigt mindestens zwei Buchungszeilen.");
        if (string.IsNullOrWhiteSpace(entry.Description)) errors.Add("Buchungstext ist erforderlich.");
        if (entry.DocumentDate > entry.BookingDate.AddYears(2)) errors.Add("Belegdatum liegt unplausibel weit nach dem Buchungsdatum.");

        decimal debit = 0m;
        decimal credit = 0m;
        for (var i = 0; i < entry.Lines.Count; i++)
        {
            var line = entry.Lines[i];
            if (string.IsNullOrWhiteSpace(line.AccountNumber)) errors.Add($"Zeile {i + 1}: Konto fehlt.");
            if (line.Debit < 0 || line.Credit < 0) errors.Add($"Zeile {i + 1}: Negative Soll-/Habenbeträge sind nicht zulässig; Korrekturen erfolgen über Gegenbuchungen.");
            if ((line.Debit > 0m) == (line.Credit > 0m)) errors.Add($"Zeile {i + 1}: Genau eine Seite, Soll oder Haben, muss größer als 0 sein.");
            if (decimal.Round(line.Debit, 2) != line.Debit || decimal.Round(line.Credit, 2) != line.Credit)
                errors.Add($"Zeile {i + 1}: Buchungsbeträge dürfen höchstens zwei Nachkommastellen haben.");
            if (line.TaxRate is < 0m or > 100m) errors.Add($"Zeile {i + 1}: Ungültiger Steuersatz.");
            if (line.TaxAmount is < 0m) errors.Add($"Zeile {i + 1}: Steuerbetrag darf nicht negativ sein.");
            debit += line.Debit;
            credit += line.Credit;
        }

        debit = decimal.Round(debit, 2, MidpointRounding.AwayFromZero);
        credit = decimal.Round(credit, 2, MidpointRounding.AwayFromZero);
        if (debit <= 0m || credit <= 0m) errors.Add("Buchungssumme muss größer als 0 sein.");
        if (debit != credit) errors.Add($"Buchung ist nicht ausgeglichen: Soll {debit:0.00} EUR, Haben {credit:0.00} EUR.");
        return new(errors, debit, credit);
    }
}

public static class GrowCentralContractBillingLedgerPolicy
{
    public static IReadOnlyList<string> ValidateScope(JournalEntryDraft entry)
    {
        var errors = new List<string>();
        if (entry.ContractId is null)
            errors.Add("Buchung ist außerhalb des GrowCentral-Vertragsabrechnungs-Scope: ContractId fehlt.");

        if (entry.SourceDocumentId is null && entry.PaymentId is null)
            errors.Add("GC-Vertragsbuchung benötigt eine Rechnungs-/Dokumentquelle oder einen Zahlungseingang.");

        if (entry.BillingPeriodId is null && entry.PaymentId is null && entry.ReversalOfEntryId is null)
            errors.Add("Abrechnungsbuchung benötigt eine BillingPeriodId; Zahlungen und Gegenbuchungen sind davon ausgenommen.");

        return errors;
    }
}

public static class AccountingPeriodKey
{
    public static (DateOnly Start, DateOnly End) ParseMonth(string periodKey)
    {
        if (periodKey.Length != 7 || periodKey[4] != '-' ||
            !int.TryParse(periodKey[..4], out var year) || !int.TryParse(periodKey[5..], out var month) ||
            year is < 2000 or > 2200 || month is < 1 or > 12)
            throw new ArgumentException("Periode muss im Format YYYY-MM angegeben werden.");
        var start = new DateOnly(year, month, 1);
        return (start, start.AddMonths(1).AddDays(-1));
    }

    public static string FromDate(DateOnly date) => $"{date:yyyy-MM}";
}
