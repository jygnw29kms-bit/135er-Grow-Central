using System.Text;

namespace GrowCentral.Backoffice.Api;

public static class ReceiptFilePolicy
{
    public static bool MatchesDeclaredMediaType(ReadOnlySpan<byte> prefix, string mediaType)
    {
        if (prefix.IsEmpty) return false;
        if (mediaType.Equals("application/pdf", StringComparison.OrdinalIgnoreCase))
            return prefix.Length >= 5 && prefix[..5].SequenceEqual("%PDF-"u8);
        if (mediaType.Equals("image/png", StringComparison.OrdinalIgnoreCase))
            return prefix.Length >= 8 && prefix[..8].SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A });
        if (mediaType.Equals("image/jpeg", StringComparison.OrdinalIgnoreCase))
            return prefix.Length >= 3 && prefix[0] == 0xFF && prefix[1] == 0xD8 && prefix[2] == 0xFF;
        if (mediaType.Equals("application/xml", StringComparison.OrdinalIgnoreCase) || mediaType.Equals("text/xml", StringComparison.OrdinalIgnoreCase))
            return LooksLikeXml(prefix);
        return false;
    }

    private static bool LooksLikeXml(ReadOnlySpan<byte> prefix)
    {
        var start = 0;
        if (prefix.Length >= 3 && prefix[0] == 0xEF && prefix[1] == 0xBB && prefix[2] == 0xBF) start = 3;
        while (start < prefix.Length && prefix[start] is (byte)' ' or (byte)'\t' or (byte)'\r' or (byte)'\n') start++;
        if (start >= prefix.Length || prefix[start] != (byte)'<') return false;
        var preview = Encoding.UTF8.GetString(prefix[start..Math.Min(prefix.Length, start + 256)]);
        return preview.StartsWith("<?xml", StringComparison.OrdinalIgnoreCase) ||
               preview.StartsWith("<rsm:", StringComparison.OrdinalIgnoreCase) ||
               preview.StartsWith("<ubl:", StringComparison.OrdinalIgnoreCase) ||
               preview.StartsWith("<Invoice", StringComparison.OrdinalIgnoreCase) ||
               preview.StartsWith("<CrossIndustryInvoice", StringComparison.OrdinalIgnoreCase);
    }
}
