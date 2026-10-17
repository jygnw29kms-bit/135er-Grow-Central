using GrowCentral.Backoffice.Domain;
using Xunit;

namespace GrowCentral.Backoffice.Domain.Tests;

public sealed class InvoiceCompliance2026Tests
{
    [Fact]
    public void Small_business_supplier_may_issue_other_invoice()
    {
        var decision = GermanEInvoicePolicy.Evaluate(new(
            new DateOnly(2028, 1, 1), true, true, 10_000m, true,
            IsSmallBusinessSupplier: true));
        Assert.Equal(EInvoiceRequirement.NotApplicable, decision.Requirement);
        Assert.Contains("§ 34a UStDV", decision.LegalReference, StringComparison.Ordinal);
    }

    [Fact]
    public void Small_amount_invoice_is_exception_even_after_transition()
    {
        var decision = GermanEInvoicePolicy.Evaluate(new(
            new DateOnly(2028, 1, 1), true, true, 2_000_000m, true,
            IsSmallAmountInvoice: true));
        Assert.Equal(EInvoiceRequirement.NotApplicable, decision.Requirement);
        Assert.Contains("§ 33 UStDV", decision.LegalReference, StringComparison.Ordinal);
    }

    [Fact]
    public void Section_4_8_to_29_exempt_transaction_is_not_forced_into_einvoice()
    {
        var decision = GermanEInvoicePolicy.Evaluate(new(
            new DateOnly(2028, 1, 1), true, true, 2_000_000m, true,
            IsExemptTransactionUnderSection4_8To29: true));
        Assert.Equal(EInvoiceRequirement.NotApplicable, decision.Requirement);
    }

    [Fact]
    public void Passenger_ticket_is_exception()
    {
        var decision = GermanEInvoicePolicy.Evaluate(new(
            new DateOnly(2028, 1, 1), true, true, 2_000_000m, true,
            IsPassengerTicket: true));
        Assert.Equal(EInvoiceRequirement.NotApplicable, decision.Requirement);
        Assert.Contains("§ 34 UStDV", decision.LegalReference, StringComparison.Ordinal);
    }

    [Fact]
    public void Standards_matrix_tracks_current_2026_versions()
    {
        Assert.Equal("3.0.2", EInvoiceStandards2026.XRechnungVersion);
        Assert.Equal("2026-08-31", EInvoiceStandards2026.XRechnungBundle);
        Assert.Equal("1.6.3", EInvoiceStandards2026.KositValidatorVersion);
        Assert.Equal("2.5.2", EInvoiceStandards2026.ZugferdVersion);
    }
}
