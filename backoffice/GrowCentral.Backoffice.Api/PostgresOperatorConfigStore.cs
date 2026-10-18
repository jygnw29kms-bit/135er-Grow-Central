using System.Text.Json;
using Npgsql;

namespace GrowCentral.Backoffice.Api;

public sealed record OperatorConfig(
    string LegalName,
    string? TradeName,
    Dictionary<string, string?> Address,
    string? TaxNumber,
    string? VatId,
    string? BusinessId,
    string? TaxOffice,
    string TaxationMode,
    string VatFilingPeriod,
    string CashOrAccrualVat,
    string ChartOfAccounts,
    decimal? PriorYearTurnover,
    decimal? CurrentYearTurnover,
    DateOnly? SmallBusinessWaiverSince,
    string LegalForm = "sole_proprietor");

public sealed record OperatorConfigValidation(IReadOnlyList<string> Errors, IReadOnlyList<string> Warnings)
{
    public bool IsValid => Errors.Count == 0;
}

public static class OperatorConfigPolicy
{
    private static readonly HashSet<string> TaxationModes = new(StringComparer.Ordinal) { "regular", "small_business" };
    private static readonly HashSet<string> FilingPeriods = new(StringComparer.Ordinal) { "monthly", "quarterly", "annual", "none" };
    private static readonly HashSet<string> VatMethods = new(StringComparer.Ordinal) { "cash", "accrual" };
    private static readonly HashSet<string> Charts = new(StringComparer.Ordinal) { "SKR03", "SKR04" };

    public static OperatorConfigValidation Validate(OperatorConfig config)
    {
        var errors = new List<string>();
        var warnings = new List<string>();
        if (string.IsNullOrWhiteSpace(config.LegalName)) errors.Add("Rechtlicher Name ist erforderlich.");
        if (config.LegalForm != "sole_proprietor") errors.Add("Dieses Projekt ist verbindlich als Einzelunternehmen konfiguriert.");
        if (!TaxationModes.Contains(config.TaxationMode)) errors.Add("taxation_mode muss regular oder small_business sein.");
        if (!FilingPeriods.Contains(config.VatFilingPeriod)) errors.Add("Ungültiger USt-Voranmeldungszeitraum.");
        if (!VatMethods.Contains(config.CashOrAccrualVat)) errors.Add("cash_or_accrual_vat muss cash oder accrual sein.");
        if (!Charts.Contains(config.ChartOfAccounts)) errors.Add("Kontenrahmen muss SKR03 oder SKR04 sein.");
        if (config.PriorYearTurnover is < 0 || config.CurrentYearTurnover is < 0) errors.Add("Umsätze dürfen nicht negativ sein.");

        if (config.TaxationMode == "small_business")
        {
            if (config.PriorYearTurnover is > 25_000m)
                errors.Add("Kleinunternehmerstatus ist bei einem Vorjahresgesamtumsatz über 25.000 EUR nach § 19 UStG nicht zulässig.");
            if (config.CurrentYearTurnover is > 100_000m)
                errors.Add("Die 100.000-EUR-Grenze des laufenden Jahres nach § 19 UStG ist überschritten; der überschreitende Umsatz ist nicht mehr steuerfrei.");
            if (config.SmallBusinessWaiverSince is not null)
                warnings.Add("Es ist ein Verzicht auf die Kleinunternehmerregelung erfasst. Bindungsfrist und wirksamer Widerruf müssen vor Anwendung geprüft werden.");
            if (config.VatFilingPeriod != "none")
                warnings.Add("Kleinunternehmer haben regelmäßig keine USt-Voranmeldungen nach § 18 Abs. 1-4 UStG; Sonderfälle bleiben möglich.");
        }
        else if (config.VatFilingPeriod == "none")
        {
            warnings.Add("Regelbesteuerung mit USt-Voranmeldungszeitraum 'none' ist nur bei gesetzlich zulässiger Ausnahme sinnvoll.");
        }

        if (string.IsNullOrWhiteSpace(config.TaxNumber) && string.IsNullOrWhiteSpace(config.VatId))
            warnings.Add("Für Rechnungen muss mindestens Steuernummer oder USt-IdNr. beziehungsweise bei Kleinunternehmern ggf. die zulässige Identifikationsnummer gepflegt werden.");
        if (!config.Address.TryGetValue("street", out var street) || string.IsNullOrWhiteSpace(street) ||
            !config.Address.TryGetValue("postal_code", out var postal) || string.IsNullOrWhiteSpace(postal) ||
            !config.Address.TryGetValue("city", out var city) || string.IsNullOrWhiteSpace(city))
            errors.Add("Vollständige Geschäftsanschrift mit Straße, PLZ und Ort ist erforderlich.");
        return new(errors, warnings);
    }
}

public sealed class PostgresOperatorConfigStore(string connectionString)
{
    private readonly string _connectionString = connectionString;

    public async Task<OperatorConfig?> GetAsync(CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        const string sql = @"SELECT legal_name,trade_name,address_json::text,tax_number,vat_id,business_id,tax_office,taxation_mode,vat_filing_period,cash_or_accrual_vat,chart_of_accounts,prior_year_turnover,current_year_turnover,small_business_waiver_since,legal_form
FROM backoffice_operator_config WHERE singleton=TRUE";
        await using var command = new NpgsqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        var address = JsonSerializer.Deserialize<Dictionary<string, string?>>(reader.GetString(2)) ?? new();
        return new(
            reader.GetString(0),
            reader.IsDBNull(1) ? null : reader.GetString(1),
            address,
            reader.IsDBNull(3) ? null : reader.GetString(3),
            reader.IsDBNull(4) ? null : reader.GetString(4),
            reader.IsDBNull(5) ? null : reader.GetString(5),
            reader.IsDBNull(6) ? null : reader.GetString(6),
            reader.GetString(7), reader.GetString(8), reader.GetString(9), reader.GetString(10),
            reader.IsDBNull(11) ? null : reader.GetDecimal(11),
            reader.IsDBNull(12) ? null : reader.GetDecimal(12),
            reader.IsDBNull(13) ? null : DateOnly.FromDateTime(reader.GetDateTime(13)),
            reader.GetString(14));
    }

    public async Task SaveAsync(OperatorConfig config, Guid actorId, CancellationToken ct)
    {
        var validation = OperatorConfigPolicy.Validate(config);
        if (!validation.IsValid) throw new ArgumentException(string.Join(" ", validation.Errors));
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string sql = @"INSERT INTO backoffice_operator_config(singleton,legal_name,trade_name,address_json,tax_number,vat_id,business_id,tax_office,taxation_mode,vat_filing_period,cash_or_accrual_vat,chart_of_accounts,prior_year_turnover,current_year_turnover,small_business_waiver_since,legal_form,updated_at,updated_by)
VALUES(TRUE,@legal_name,@trade_name,@address::jsonb,@tax_number,@vat_id,@business_id,@tax_office,@taxation_mode,@filing,@vat_method,@chart,@prior,@current,@waiver,'sole_proprietor',NOW(),@actor)
ON CONFLICT(singleton) DO UPDATE SET legal_name=EXCLUDED.legal_name,trade_name=EXCLUDED.trade_name,address_json=EXCLUDED.address_json,tax_number=EXCLUDED.tax_number,vat_id=EXCLUDED.vat_id,business_id=EXCLUDED.business_id,tax_office=EXCLUDED.tax_office,taxation_mode=EXCLUDED.taxation_mode,vat_filing_period=EXCLUDED.vat_filing_period,cash_or_accrual_vat=EXCLUDED.cash_or_accrual_vat,chart_of_accounts=EXCLUDED.chart_of_accounts,prior_year_turnover=EXCLUDED.prior_year_turnover,current_year_turnover=EXCLUDED.current_year_turnover,small_business_waiver_since=EXCLUDED.small_business_waiver_since,updated_at=NOW(),updated_by=EXCLUDED.updated_by";
        await using (var command = new NpgsqlCommand(sql, connection, tx))
        {
            command.Parameters.AddWithValue("legal_name", config.LegalName.Trim());
            command.Parameters.AddWithValue("trade_name", (object?)config.TradeName ?? DBNull.Value);
            command.Parameters.AddWithValue("address", JsonSerializer.Serialize(config.Address));
            command.Parameters.AddWithValue("tax_number", (object?)config.TaxNumber ?? DBNull.Value);
            command.Parameters.AddWithValue("vat_id", (object?)config.VatId ?? DBNull.Value);
            command.Parameters.AddWithValue("business_id", (object?)config.BusinessId ?? DBNull.Value);
            command.Parameters.AddWithValue("tax_office", (object?)config.TaxOffice ?? DBNull.Value);
            command.Parameters.AddWithValue("taxation_mode", config.TaxationMode);
            command.Parameters.AddWithValue("filing", config.VatFilingPeriod);
            command.Parameters.AddWithValue("vat_method", config.CashOrAccrualVat);
            command.Parameters.AddWithValue("chart", config.ChartOfAccounts);
            command.Parameters.AddWithValue("prior", (object?)config.PriorYearTurnover ?? DBNull.Value);
            command.Parameters.AddWithValue("current", (object?)config.CurrentYearTurnover ?? DBNull.Value);
            command.Parameters.AddWithValue("waiver", config.SmallBusinessWaiverSince is null ? DBNull.Value : config.SmallBusinessWaiverSince.Value.ToDateTime(TimeOnly.MinValue));
            command.Parameters.AddWithValue("actor", actorId.ToString());
            await command.ExecuteNonQueryAsync(ct);
        }
        const string auditSql = @"INSERT INTO backoffice_audit_events(id,occurred_at,actor_id,action,entity_type,entity_id,entity_version,payload_hash,payload)
VALUES(@id,NOW(),@actor,'OperatorConfigChanged','OperatorConfig','singleton',1,@hash,@payload::jsonb)";
        var payload = JsonSerializer.Serialize(new { config.TaxationMode, config.VatFilingPeriod, config.CashOrAccrualVat, config.ChartOfAccounts, config.PriorYearTurnover, config.CurrentYearTurnover });
        await using (var audit = new NpgsqlCommand(auditSql, connection, tx))
        {
            audit.Parameters.AddWithValue("id", Guid.NewGuid());
            audit.Parameters.AddWithValue("actor", actorId.ToString());
            audit.Parameters.AddWithValue("hash", BackofficeTotp.HashToken(payload));
            audit.Parameters.AddWithValue("payload", payload);
            await audit.ExecuteNonQueryAsync(ct);
        }
        await tx.CommitAsync(ct);
    }

    private async Task<NpgsqlConnection> OpenAsync(CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(_connectionString)) throw new InvalidOperationException("GC_BACKOFFICE_DB ist nicht konfiguriert.");
        var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(ct);
        return connection;
    }
}
