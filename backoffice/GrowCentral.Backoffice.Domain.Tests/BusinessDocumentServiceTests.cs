using GrowCentral.Backoffice.Domain;
using Xunit;

namespace GrowCentral.Backoffice.Domain.Tests;

public class BusinessDocumentServiceTests
{
    [Fact]
    public void CatalogContainsAllMasterTemplates()
    {
        Assert.Equal(47, BusinessDocumentCatalog.All.Count);
        Assert.Contains("A1", BusinessDocumentCatalog.All.Keys);
        Assert.Contains("H5", BusinessDocumentCatalog.All.Keys);
    }

    [Fact]
    public void EveryTemplateHasServerSideNumberSequence()
    {
        foreach (var code in BusinessDocumentCatalog.All.Keys)
        {
            var policy = BusinessDocumentSequenceCatalog.Get(code);
            Assert.False(string.IsNullOrWhiteSpace(policy.SequenceKey));
            Assert.False(string.IsNullOrWhiteSpace(policy.Prefix));
        }
    }

    [Fact]
    public void FinalizedInvoiceCannotBeSilentlyChanged()
    {
        var invoice = ValidB2BInvoice();
        var service = new BusinessDocumentService();
        service.Finalize(invoice, "owner", DomesticB2B(new DateOnly(2026, 10, 17), 100_000m));

        Assert.Throws<InvalidOperationException>(() => invoice.SetValue("gross_amount", "999.00"));
        Assert.Throws<InvalidOperationException>(() => invoice.AddLink(Guid.NewGuid(), "tamper"));
    }

    [Fact]
    public void DraftCannotBeMarkedSettled()
    {
        var invoice = ValidB2BInvoice();
        Assert.Throws<InvalidOperationException>(() => invoice.MarkSettled());
    }

    [Fact]
    public void MissingB2BComplianceContextBlocksFinalization()
    {
        var result = new BusinessDocumentService().ValidateForFinalization(ValidB2BInvoice());

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "invoice.compliance_context_missing");
    }

    [Fact]
    public void TransitionRuleAllowsOtherInvoiceThroughEndOf2026()
    {
        var invoice = ValidB2BInvoice();
        invoice.SetValue("e_invoice_format", null);

        var result = new BusinessDocumentService().ValidateForFinalization(
            invoice,
            DomesticB2B(new DateOnly(2026, 12, 31), 2_000_000m));

        Assert.True(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "invoice.einvoice_transition" && !x.IsBlocking);
    }

    [Fact]
    public void SmallSupplierTransitionContinuesThrough2027()
    {
        var decision = GermanEInvoicePolicy.Evaluate(DomesticB2B(new DateOnly(2027, 8, 1), 800_000m));
        Assert.Equal(EInvoiceRequirement.TransitionalAlternativeAllowed, decision.Requirement);
    }

    [Fact]
    public void LargeSupplierRequiresStructuredInvoiceIn2027()
    {
        var invoice = ValidB2BInvoice();
        invoice.SetValue("e_invoice_format", null);

        var result = new BusinessDocumentService().ValidateForFinalization(
            invoice,
            DomesticB2B(new DateOnly(2027, 8, 1), 800_000.01m));

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "invoice.einvoice_required");
    }

    [Fact]
    public void StructuredInvoiceIsRequiredFrom2028ForDomesticB2B()
    {
        var invoice = ValidB2BInvoice();
        invoice.SetValue("e_invoice_format", null);

        var result = new BusinessDocumentService().ValidateForFinalization(
            invoice,
            DomesticB2B(new DateOnly(2028, 1, 1), 10_000m));

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "invoice.einvoice_required");
    }

    [Fact]
    public void ConsumerDunningRejectsFortyEuroFlatFee()
    {
        var dunning = new BusinessDocument { TemplateCode = "B7", Number = "MA-1", PartyType = PartyType.Consumer, CreatedBy = "owner" };
        FillBase(dunning);
        dunning.SetValue("invoice_id", Guid.NewGuid().ToString());
        dunning.SetValue("principal", "100.00");
        dunning.SetValue("deadline", "2026-11-01");
        dunning.SetValue("late_fee_40_eur", "true");

        var result = new BusinessDocumentService().ValidateForFinalization(dunning);

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "dunning.consumer_40eur_forbidden");
    }

    [Fact]
    public void LegalReviewTemplateMustBeApproved()
    {
        var nda = new BusinessDocument { TemplateCode = "E3", Number = "NDA-1", PartyType = PartyType.Business, CreatedBy = "owner" };
        FillBase(nda);
        nda.SetValue("purpose", "Projektprüfung");
        nda.SetValue("confidential_scope", "Technische und kaufmännische Informationen");
        nda.SetValue("duration", "24 Monate");

        var result = new BusinessDocumentService().ValidateForFinalization(nda);

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "legal.review_required");
    }

    [Fact]
    public void DraftCorrectionDoesNotChangeOriginalUntilCorrectionFinalizes()
    {
        var invoice = ValidB2BInvoice();
        var service = new BusinessDocumentService();
        var context = DomesticB2B(new DateOnly(2026, 10, 17), 100_000m);
        service.Finalize(invoice, "owner", context);

        var correction = service.CreateCorrection(invoice, "RK-2026-0001", "owner", "Preisberichtigung");
        correction.SetValue("gross_amount", "-119.00");

        Assert.Equal(BusinessDocumentStatus.Finalized, invoice.Status);
        Assert.Equal(BusinessDocumentStatus.Draft, correction.Status);
        Assert.Contains(correction.Links, x => x.TargetDocumentId == invoice.Id && x.Relation == "corrects");

        service.FinalizeCorrection(invoice, correction, "owner", context);

        Assert.Equal(BusinessDocumentStatus.Corrected, invoice.Status);
        Assert.Equal(BusinessDocumentStatus.Finalized, correction.Status);
    }

    [Fact]
    public void OptionalTemplatePlaceholdersDoNotBlockFinalOutput()
    {
        var invoice = ValidB2BInvoice();
        var rendered = new BusinessDocumentRenderer().Render(invoice);
        var output = BusinessDocumentOutputPolicy.Prepare(invoice, rendered);

        Assert.Empty(output.BlockingMissingValues);
        Assert.Contains("bank_details", output.OptionalMissingValues);
        Assert.DoesNotContain("[bank_details]", output.Body, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void RequiredTemplatePlaceholderStillBlocksFinalOutput()
    {
        var invoice = ValidB2BInvoice();
        invoice.SetValue("invoice_number", null);
        var rendered = new BusinessDocumentRenderer().Render(invoice);
        var output = BusinessDocumentOutputPolicy.Prepare(invoice, rendered);

        Assert.Contains("invoice_number", output.BlockingMissingValues);
    }

    [Fact]
    public void NumberFormatterProducesStableNumber()
    {
        var number = DocumentNumberFormatter.Format(new("invoice", "RE", 2026, 6), 42);
        Assert.Equal("RE-2026-000042", number);
    }

    private static BusinessDocument ValidB2BInvoice()
    {
        var invoice = new BusinessDocument { TemplateCode = "B1", Number = "RE-2026-0001", PartyType = PartyType.Business, CreatedBy = "owner" };
        FillBase(invoice);
        invoice.SetValue("invoice_number", "RE-2026-0001");
        invoice.SetValue("service_date", "2026-10-17");
        invoice.SetValue("seller_tax_id", "CONFIGURED-CENTRALLY");
        invoice.SetValue("items", "GrowCentral Leistung");
        invoice.SetValue("net_amount", "100.00");
        invoice.SetValue("tax_amount", "19.00");
        invoice.SetValue("gross_amount", "119.00");
        invoice.SetValue("due_date", "2026-10-31");
        invoice.SetValue("e_invoice_format", "xrechnung");
        return invoice;
    }

    private static InvoiceComplianceContext DomesticB2B(DateOnly supplyDate, decimal priorYearTurnover) =>
        new(supplyDate, true, true, priorYearTurnover, true);

    private static void FillBase(BusinessDocument document)
    {
        document.SetValue("party_name", "Testkunde");
        document.SetValue("party_address", "Musterstraße 1, 12345 Musterstadt");
        document.SetValue("document_date", "2026-10-17");
    }
}
