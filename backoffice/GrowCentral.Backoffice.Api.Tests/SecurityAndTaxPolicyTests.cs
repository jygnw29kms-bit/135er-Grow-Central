using GrowCentral.Backoffice.Api;

namespace GrowCentral.Backoffice.Api.Tests;

public sealed class SecurityAndTaxPolicyTests
{
    [Fact]
    public void Password_hash_roundtrips_and_wrong_password_fails()
    {
        const string password = "SehrLangesPasswort2026";
        var hash = BackofficePasswordHasher.Hash(password);
        Assert.True(BackofficePasswordHasher.Verify(password, hash));
        Assert.False(BackofficePasswordHasher.Verify("FalschesPasswort2026", hash));
        Assert.DoesNotContain(password, hash, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("zuKurz1A")]
    [InlineData("nurkleinbuchstaben123456")]
    [InlineData("NURGROSSBUCHSTABEN123456")]
    [InlineData("KeineZifferImPasswort")]
    public void Weak_passwords_are_rejected(string password)
    {
        Assert.Throws<ArgumentException>(() => BackofficePasswordHasher.ValidatePassword(password));
    }

    [Fact]
    public void Totp_matches_rfc6238_sha1_vector_as_six_digits()
    {
        const string secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ";
        Assert.True(BackofficeTotp.Validate(secret, "287082", DateTimeOffset.FromUnixTimeSeconds(59)));
        Assert.False(BackofficeTotp.Validate(secret, "000000", DateTimeOffset.FromUnixTimeSeconds(59)));
    }

    [Fact]
    public void Secret_protector_roundtrips_without_plaintext_storage()
    {
        var key = Convert.ToBase64String(Enumerable.Range(1, 32).Select(x => (byte)x).ToArray());
        var protector = new BackofficeSecretProtector(key);
        const string secret = "JBSWY3DPEHPK3PXP";
        var protectedValue = protector.Protect(secret);
        Assert.DoesNotContain(secret, protectedValue, StringComparison.Ordinal);
        Assert.Equal(secret, protector.Unprotect(protectedValue));
    }

    [Fact]
    public void Rbac_separates_finance_support_and_owner_privileges()
    {
        Assert.True(BackofficeRoles.CanWriteDocuments(BackofficeRoles.Owner));
        Assert.True(BackofficeRoles.CanWriteDocuments(BackofficeRoles.Billing));
        Assert.False(BackofficeRoles.CanWriteDocuments(BackofficeRoles.Support));
        Assert.False(BackofficeRoles.CanWriteDocuments(BackofficeRoles.ReadOnly));
        Assert.True(BackofficeRoles.CanConfigure(BackofficeRoles.Owner));
        Assert.False(BackofficeRoles.CanConfigure(BackofficeRoles.Billing));
    }

    [Fact]
    public void Small_business_config_rejects_statutory_turnover_limit_violation()
    {
        var config = ValidConfig() with { TaxationMode = "small_business", PriorYearTurnover = 25_000.01m };
        var result = OperatorConfigPolicy.Validate(config);
        Assert.False(result.IsValid);
        Assert.Contains(result.Errors, x => x.Contains("25.000", StringComparison.Ordinal));
    }

    [Fact]
    public void Small_business_current_year_limit_is_guarded()
    {
        var config = ValidConfig() with { TaxationMode = "small_business", CurrentYearTurnover = 100_000.01m };
        var result = OperatorConfigPolicy.Validate(config);
        Assert.False(result.IsValid);
        Assert.Contains(result.Errors, x => x.Contains("100.000", StringComparison.Ordinal));
    }

    [Fact]
    public void Sole_proprietor_legal_form_is_binding()
    {
        var config = ValidConfig() with { LegalForm = "gmbh" };
        Assert.False(OperatorConfigPolicy.Validate(config).IsValid);
    }

    private static OperatorConfig ValidConfig() => new(
        "Max Mustermann",
        "GrowCentral",
        new Dictionary<string, string?>
        {
            ["street"] = "Musterstraße 1",
            ["postal_code"] = "12345",
            ["city"] = "Berlin",
            ["country_code"] = "DE"
        },
        "12/345/67890",
        null,
        null,
        "Finanzamt Musterstadt",
        "regular",
        "monthly",
        "cash",
        "SKR03",
        20_000m,
        30_000m,
        null);
}
