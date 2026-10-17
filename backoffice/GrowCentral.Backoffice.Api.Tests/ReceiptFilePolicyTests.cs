using System.Text;
using GrowCentral.Backoffice.Api;
using Xunit;

namespace GrowCentral.Backoffice.Api.Tests;

public sealed class ReceiptFilePolicyTests
{
    [Fact]
    public void Pdf_signature_is_required()
    {
        Assert.True(ReceiptFilePolicy.MatchesDeclaredMediaType("%PDF-1.7"u8, "application/pdf"));
        Assert.False(ReceiptFilePolicy.MatchesDeclaredMediaType("<xml/>"u8, "application/pdf"));
    }

    [Fact]
    public void Png_and_jpeg_magic_are_checked()
    {
        Assert.True(ReceiptFilePolicy.MatchesDeclaredMediaType(new byte[] { 0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A }, "image/png"));
        Assert.True(ReceiptFilePolicy.MatchesDeclaredMediaType(new byte[] { 0xFF,0xD8,0xFF,0xE0 }, "image/jpeg"));
        Assert.False(ReceiptFilePolicy.MatchesDeclaredMediaType(new byte[] { 0x89,0x50,0x4E }, "image/png"));
    }

    [Theory]
    [InlineData("<?xml version=\"1.0\"?><Invoice/>")]
    [InlineData("  <Invoice></Invoice>")]
    [InlineData("<rsm:CrossIndustryInvoice></rsm:CrossIndustryInvoice>")]
    public void Expected_invoice_xml_roots_are_accepted(string xml)
    {
        Assert.True(ReceiptFilePolicy.MatchesDeclaredMediaType(Encoding.UTF8.GetBytes(xml), "application/xml"));
    }

    [Fact]
    public void Arbitrary_html_is_not_accepted_as_xml_invoice()
    {
        Assert.False(ReceiptFilePolicy.MatchesDeclaredMediaType("<html><script>x</script></html>"u8, "application/xml"));
    }
}
