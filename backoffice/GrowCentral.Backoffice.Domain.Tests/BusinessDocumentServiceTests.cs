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
    public void FinalizedInvoiceCannotBeSilentlyChanged()
    {
        var invoice = ValidB2BInvoice();
        var service = new BusinessDocumentService();
        service.Finalize(invoice, "owner");

        Assert.Throws<InvalidOperationException>(() => invoice.SetValue("gross_amount", "999.00"));
    }

    [Fact]
    public void B2BInvoiceRequiresStructuredEInvoiceFormat()
    {
        var invoice = ValidB2BInvoice();
        invoice.SetValue("e_invoice_format", null);

        var result = new BusinessDocumentService().ValidateForFinalization(invoice);

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, x => x.Code == "invoice.einvoice_format_missing");
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
    public void CorrectionLinksOriginalAndMarksItCorrected()
    {
        var invoice = ValidB2BInvoice();
        var service = new BusinessDocumentService();
        service.Finalize(invoice, "owner");

        var correction = service.CreateCorrection(invoice, "RK-2026-0001", "owner", "Preisberichtigung");

        Assert.Equal(BusinessDocumentStatus.Corrected, invoice.Status);
        Assert.Contains(correction.Links, x => x.TargetDocumentId == invoice.Id && x.Relation == "corrects");
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

    private static void FillBase(BusinessDocument document)
    {
        document.SetValue("party_name", "Testkunde");
        document.SetValue("party_address", "Musterstraße 1, 12345 Musterstadt");
        document.SetValue("document_date", "2026-10-17");
    }
}
