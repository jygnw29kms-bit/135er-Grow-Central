using GrowCentral.Backoffice.Domain;
using Xunit;

namespace GrowCentral.Backoffice.Domain.Tests;

public sealed class AccountingLedgerTests
{
    [Fact]
    public void Balanced_entry_is_valid()
    {
        var entry = new JournalEntryDraft(
            new DateOnly(2026, 10, 17),
            new DateOnly(2026, 10, 17),
            "Ausgangsrechnung",
            "RE-2026-000001",
            null,
            new[]
            {
                new JournalLine("1200", 119m, 0m),
                new JournalLine("8400", 0m, 100m),
                new JournalLine("1776", 0m, 19m, "U19", 19m, 19m)
            });

        var result = DoubleEntryLedgerPolicy.Validate(entry);
        Assert.True(result.IsValid);
        Assert.Equal(119m, result.DebitTotal);
        Assert.Equal(119m, result.CreditTotal);
    }

    [Fact]
    public void Unbalanced_entry_is_rejected()
    {
        var entry = new JournalEntryDraft(
            new DateOnly(2026, 10, 17),
            new DateOnly(2026, 10, 17),
            "Fehlerhafte Buchung",
            null,
            null,
            new[] { new JournalLine("1200", 119m, 0m), new JournalLine("8400", 0m, 100m) });

        var result = DoubleEntryLedgerPolicy.Validate(entry);
        Assert.False(result.IsValid);
        Assert.Contains(result.Errors, x => x.Contains("nicht ausgeglichen", StringComparison.Ordinal));
    }

    [Fact]
    public void Negative_amounts_are_rejected_instead_of_mutating_history()
    {
        var entry = new JournalEntryDraft(
            new DateOnly(2026, 10, 17), new DateOnly(2026, 10, 17), "Korrektur", null, null,
            new[] { new JournalLine("1200", -10m, 0m), new JournalLine("8400", 0m, 10m) });
        Assert.False(DoubleEntryLedgerPolicy.Validate(entry).IsValid);
    }

    [Fact]
    public void Period_key_roundtrips_month_boundaries()
    {
        var (start, end) = AccountingPeriodKey.ParseMonth("2026-02");
        Assert.Equal(new DateOnly(2026, 2, 1), start);
        Assert.Equal(new DateOnly(2026, 2, 28), end);
        Assert.Equal("2026-02", AccountingPeriodKey.FromDate(end));
    }
}
