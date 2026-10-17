using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace GrowCentral.Backoffice.Api;

public sealed record BackofficeActor(Guid UserId, string Username, string Role)
{
    public bool IsOwner => string.Equals(Role, BackofficeRoles.Owner, StringComparison.Ordinal);
}

public static class BackofficeRoles
{
    public const string Owner = "Owner";
    public const string Billing = "Billing";
    public const string Support = "Support";
    public const string ReadOnly = "ReadOnly";

    public static readonly IReadOnlySet<string> All = new HashSet<string>(StringComparer.Ordinal)
    {
        Owner, Billing, Support, ReadOnly
    };

    public static bool CanRead(string role) => All.Contains(role);
    public static bool CanWriteDocuments(string role) => role is Owner or Billing;
    public static bool CanApprove(string role) => role is Owner or Billing;
    public static bool CanConfigure(string role) => role == Owner;
    public static bool CanManageUsers(string role) => role == Owner;
}

public static class BackofficePasswordHasher
{
    private const int Iterations = 210_000;
    private const int SaltBytes = 16;
    private const int HashBytes = 32;

    public static string Hash(string password)
    {
        ValidatePassword(password);
        var salt = RandomNumberGenerator.GetBytes(SaltBytes);
        var hash = Rfc2898DeriveBytes.Pbkdf2(password, salt, Iterations, HashAlgorithmName.SHA256, HashBytes);
        return $"pbkdf2-sha256${Iterations.ToString(CultureInfo.InvariantCulture)}${Convert.ToBase64String(salt)}${Convert.ToBase64String(hash)}";
    }

    public static bool Verify(string password, string encoded)
    {
        var parts = encoded.Split('$');
        if (parts.Length != 4 || parts[0] != "pbkdf2-sha256") return false;
        if (!int.TryParse(parts[1], NumberStyles.None, CultureInfo.InvariantCulture, out var iterations) || iterations < 100_000) return false;
        try
        {
            var salt = Convert.FromBase64String(parts[2]);
            var expected = Convert.FromBase64String(parts[3]);
            var actual = Rfc2898DeriveBytes.Pbkdf2(password, salt, iterations, HashAlgorithmName.SHA256, expected.Length);
            return CryptographicOperations.FixedTimeEquals(actual, expected);
        }
        catch (FormatException)
        {
            return false;
        }
    }

    public static void ValidatePassword(string password)
    {
        if (password.Length < 14 || password.Length > 200)
            throw new ArgumentException("Passwort muss 14 bis 200 Zeichen lang sein.");
        if (!password.Any(char.IsUpper) || !password.Any(char.IsLower) || !password.Any(char.IsDigit))
            throw new ArgumentException("Passwort muss Groß-/Kleinbuchstaben und mindestens eine Ziffer enthalten.");
    }
}

public static class BackofficeTotp
{
    private const string Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    public static string GenerateSecret() => Base32Encode(RandomNumberGenerator.GetBytes(20));

    public static string BuildOtpAuthUri(string secret, string username) =>
        $"otpauth://totp/{Uri.EscapeDataString("GrowCentral Backoffice")}:{Uri.EscapeDataString(username)}?secret={secret}&issuer={Uri.EscapeDataString("GrowCentral Backoffice")}&algorithm=SHA1&digits=6&period=30";

    public static bool Validate(string secret, string code, DateTimeOffset now)
    {
        var normalized = new string(code.Where(char.IsDigit).ToArray());
        if (normalized.Length != 6) return false;
        var counter = now.ToUnixTimeSeconds() / 30;
        for (long delta = -1; delta <= 1; delta++)
            if (FixedEquals(normalized, Compute(secret, counter + delta))) return true;
        return false;
    }

    private static string Compute(string secret, long counter)
    {
        var key = Base32Decode(secret);
        Span<byte> data = stackalloc byte[8];
        for (var i = 7; i >= 0; i--)
        {
            data[i] = (byte)(counter & 0xff);
            counter >>= 8;
        }
        using var hmac = new HMACSHA1(key);
        var hash = hmac.ComputeHash(data.ToArray());
        var offset = hash[^1] & 0x0f;
        var binary = ((hash[offset] & 0x7f) << 24) | (hash[offset + 1] << 16) | (hash[offset + 2] << 8) | hash[offset + 3];
        return (binary % 1_000_000).ToString("D6", CultureInfo.InvariantCulture);
    }

    public static string NewSessionToken() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_');
    public static string HashToken(string token) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(token))).ToLowerInvariant();

    private static bool FixedEquals(string left, string right)
    {
        var a = Encoding.ASCII.GetBytes(left);
        var b = Encoding.ASCII.GetBytes(right);
        return a.Length == b.Length && CryptographicOperations.FixedTimeEquals(a, b);
    }

    private static string Base32Encode(byte[] data)
    {
        var output = new StringBuilder((data.Length * 8 + 4) / 5);
        var buffer = 0;
        var bitsLeft = 0;
        foreach (var b in data)
        {
            buffer = (buffer << 8) | b;
            bitsLeft += 8;
            while (bitsLeft >= 5)
            {
                output.Append(Alphabet[(buffer >> (bitsLeft - 5)) & 31]);
                bitsLeft -= 5;
            }
        }
        if (bitsLeft > 0) output.Append(Alphabet[(buffer << (5 - bitsLeft)) & 31]);
        return output.ToString();
    }

    private static byte[] Base32Decode(string text)
    {
        var bytes = new List<byte>();
        var buffer = 0;
        var bitsLeft = 0;
        foreach (var c in text.Trim().TrimEnd('=').ToUpperInvariant())
        {
            var value = Alphabet.IndexOf(c);
            if (value < 0) throw new FormatException("Ungültiges TOTP-Secret.");
            buffer = (buffer << 5) | value;
            bitsLeft += 5;
            if (bitsLeft >= 8)
            {
                bytes.Add((byte)((buffer >> (bitsLeft - 8)) & 0xff));
                bitsLeft -= 8;
            }
        }
        return bytes.ToArray();
    }
}
