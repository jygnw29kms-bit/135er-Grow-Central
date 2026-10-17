using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using GrowCentral.Backoffice.Domain;
using Npgsql;

namespace GrowCentral.Backoffice.Api;

public sealed record LedgerAccount(string AccountNumber, string ChartOfAccounts, string AccountName, string AccountType, bool Active = true);
public sealed record PostedJournalEntry(Guid Id, string EntryNumber, DateOnly BookingDate, DateOnly DocumentDate, string Description, string? Reference, Guid? SourceDocumentId, Guid? ReversalOfEntryId, string ContentHash, DateTimeOffset PostedAt, string PostedBy);

public sealed class PostgresLedgerStore(string connectionString)
{
    private readonly string _connectionString = connectionString;

    public async Task CreateAccountAsync(LedgerAccount account, Guid actorId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(account.AccountNumber) || account.AccountNumber.Length > 16) throw new ArgumentException("Ungültige Kontonummer.");
        if (account.ChartOfAccounts is not ("SKR03" or "SKR04")) throw new ArgumentException("Kontenrahmen muss SKR03 oder SKR04 sein.");
        if (account.AccountType is not ("asset" or "liability" or "equity" or "revenue" or "expense" or "tax" or "clearing")) throw new ArgumentException("Ungültiger Kontotyp.");
        if (string.IsNullOrWhiteSpace(account.AccountName)) throw new ArgumentException("Kontoname ist erforderlich.");

        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string sql = @"INSERT INTO backoffice_accounts(account_number,chart_of_accounts,account_name,account_type,active,system_defined)
VALUES(@number,@chart,@name,@type,@active,FALSE)";
        await using (var command = new NpgsqlCommand(sql, connection, tx))
        {
            command.Parameters.AddWithValue("number", account.AccountNumber.Trim());
            command.Parameters.AddWithValue("chart", account.ChartOfAccounts);
            command.Parameters.AddWithValue("name", account.AccountName.Trim());
            command.Parameters.AddWithValue("type", account.AccountType);
            command.Parameters.AddWithValue("active", account.Active);
            await command.ExecuteNonQueryAsync(ct);
        }
        await AppendAuditAsync(connection, tx, actorId, "LedgerAccountCreated", account.AccountNumber, JsonSerializer.Serialize(account), ct);
        await tx.CommitAsync(ct);
    }

    public async Task<PostedJournalEntry> PostAsync(JournalEntryDraft draft, Guid actorId, CancellationToken ct)
    {
        var validation = DoubleEntryLedgerPolicy.Validate(draft);
        if (!validation.IsValid) throw new ArgumentException(string.Join(" ", validation.Errors));
        var periodKey = AccountingPeriodKey.FromDate(draft.BookingDate);
        var (periodStart, periodEnd) = AccountingPeriodKey.ParseMonth(periodKey);
        var payload = JsonSerializer.Serialize(draft);
        var hash = Sha256(payload);
        var id = Guid.NewGuid();
        var postedAt = DateTimeOffset.UtcNow;

        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        await EnsurePeriodOpenAsync(connection, tx, periodKey, periodStart, periodEnd, ct);

        var entryNumber = await NextNumberAsync(connection, tx, draft.BookingDate.Year, ct);
        const string entrySql = @"INSERT INTO backoffice_journal_entries
(id,entry_number,booking_date,document_date,description,reference,source_document_id,reversal_of_entry_id,status,content_hash,posted_at,posted_by)
VALUES(@id,@number,@booking_date,@document_date,@description,@reference,@source_document,@reversal_of,'posted',@hash,@posted_at,@posted_by)";
        await using (var command = new NpgsqlCommand(entrySql, connection, tx))
        {
            command.Parameters.AddWithValue("id", id);
            command.Parameters.AddWithValue("number", entryNumber);
            command.Parameters.AddWithValue("booking_date", draft.BookingDate.ToDateTime(TimeOnly.MinValue));
            command.Parameters.AddWithValue("document_date", draft.DocumentDate.ToDateTime(TimeOnly.MinValue));
            command.Parameters.AddWithValue("description", draft.Description.Trim());
            command.Parameters.AddWithValue("reference", (object?)draft.Reference ?? DBNull.Value);
            command.Parameters.AddWithValue("source_document", draft.SourceDocumentId.HasValue ? draft.SourceDocumentId.Value : DBNull.Value);
            command.Parameters.AddWithValue("reversal_of", draft.ReversalOfEntryId.HasValue ? draft.ReversalOfEntryId.Value : DBNull.Value);
            command.Parameters.AddWithValue("hash", hash);
            command.Parameters.AddWithValue("posted_at", postedAt.UtcDateTime);
            command.Parameters.AddWithValue("posted_by", actorId.ToString());
            await command.ExecuteNonQueryAsync(ct);
        }

        const string lineSql = @"INSERT INTO backoffice_journal_lines
(id,journal_entry_id,line_number,account_number,debit,credit,tax_code,tax_rate,tax_amount,party_id,document_id,memo)
VALUES(@id,@entry_id,@line_number,@account,@debit,@credit,@tax_code,@tax_rate,@tax_amount,@party_id,@document_id,@memo)";
        for (var i = 0; i < draft.Lines.Count; i++)
        {
            var line = draft.Lines[i];
            await using var command = new NpgsqlCommand(lineSql, connection, tx);
            command.Parameters.AddWithValue("id", Guid.NewGuid());
            command.Parameters.AddWithValue("entry_id", id);
            command.Parameters.AddWithValue("line_number", i + 1);
            command.Parameters.AddWithValue("account", line.AccountNumber.Trim());
            command.Parameters.AddWithValue("debit", line.Debit);
            command.Parameters.AddWithValue("credit", line.Credit);
            command.Parameters.AddWithValue("tax_code", (object?)line.TaxCode ?? DBNull.Value);
            command.Parameters.AddWithValue("tax_rate", line.TaxRate.HasValue ? line.TaxRate.Value : DBNull.Value);
            command.Parameters.AddWithValue("tax_amount", line.TaxAmount.HasValue ? line.TaxAmount.Value : DBNull.Value);
            command.Parameters.AddWithValue("party_id", line.PartyId.HasValue ? line.PartyId.Value : DBNull.Value);
            command.Parameters.AddWithValue("document_id", line.DocumentId.HasValue ? line.DocumentId.Value : DBNull.Value);
            command.Parameters.AddWithValue("memo", (object?)line.Memo ?? DBNull.Value);
            await command.ExecuteNonQueryAsync(ct);
        }

        await AppendAuditAsync(connection, tx, actorId, draft.ReversalOfEntryId.HasValue ? "JournalReversalPosted" : "JournalPosted", id.ToString(), payload, ct);
        await tx.CommitAsync(ct);
        return new(id, entryNumber, draft.BookingDate, draft.DocumentDate, draft.Description, draft.Reference, draft.SourceDocumentId, draft.ReversalOfEntryId, hash, postedAt, actorId.ToString());
    }

    public async Task LockPeriodAsync(string periodKey, Guid actorId, CancellationToken ct)
    {
        var (start, end) = AccountingPeriodKey.ParseMonth(periodKey);
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string sql = @"INSERT INTO backoffice_accounting_periods(period_key,starts_on,ends_on,status,locked_at,locked_by)
VALUES(@key,@start,@end,'locked',NOW(),@actor)
ON CONFLICT(period_key) DO UPDATE SET status='locked',locked_at=NOW(),locked_by=EXCLUDED.locked_by,reopened_at=NULL,reopened_by=NULL,reopen_reason=NULL
WHERE backoffice_accounting_periods.status IN ('open','closing','reopened')";
        await using (var command = new NpgsqlCommand(sql, connection, tx))
        {
            command.Parameters.AddWithValue("key", periodKey);
            command.Parameters.AddWithValue("start", start.ToDateTime(TimeOnly.MinValue));
            command.Parameters.AddWithValue("end", end.ToDateTime(TimeOnly.MinValue));
            command.Parameters.AddWithValue("actor", actorId.ToString());
            if (await command.ExecuteNonQueryAsync(ct) != 1) throw new InvalidOperationException("Periode ist bereits gesperrt oder nicht sperrbar.");
        }
        await AppendAuditAsync(connection, tx, actorId, "AccountingPeriodLocked", periodKey, "{}", ct);
        await tx.CommitAsync(ct);
    }

    public async Task ReopenPeriodAsync(string periodKey, string reason, Guid actorId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(reason) || reason.Trim().Length < 8) throw new ArgumentException("Wiedereröffnung benötigt eine nachvollziehbare Begründung.");
        AccountingPeriodKey.ParseMonth(periodKey);
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string sql = @"UPDATE backoffice_accounting_periods
SET status='reopened',reopened_at=NOW(),reopened_by=@actor,reopen_reason=@reason
WHERE period_key=@key AND status='locked'";
        await using (var command = new NpgsqlCommand(sql, connection, tx))
        {
            command.Parameters.AddWithValue("actor", actorId.ToString());
            command.Parameters.AddWithValue("reason", reason.Trim());
            command.Parameters.AddWithValue("key", periodKey);
            if (await command.ExecuteNonQueryAsync(ct) != 1) throw new InvalidOperationException("Nur eine gesperrte Periode kann wieder geöffnet werden.");
        }
        await AppendAuditAsync(connection, tx, actorId, "AccountingPeriodReopened", periodKey, JsonSerializer.Serialize(new { reason = reason.Trim() }), ct);
        await tx.CommitAsync(ct);
    }

    private static async Task EnsurePeriodOpenAsync(NpgsqlConnection connection, NpgsqlTransaction tx, string key, DateOnly start, DateOnly end, CancellationToken ct)
    {
        const string insert = @"INSERT INTO backoffice_accounting_periods(period_key,starts_on,ends_on,status)
VALUES(@key,@start,@end,'open') ON CONFLICT(period_key) DO NOTHING";
        await using (var command = new NpgsqlCommand(insert, connection, tx))
        {
            command.Parameters.AddWithValue("key", key);
            command.Parameters.AddWithValue("start", start.ToDateTime(TimeOnly.MinValue));
            command.Parameters.AddWithValue("end", end.ToDateTime(TimeOnly.MinValue));
            await command.ExecuteNonQueryAsync(ct);
        }
        await using var status = new NpgsqlCommand("SELECT status FROM backoffice_accounting_periods WHERE period_key=@key FOR UPDATE", connection, tx);
        status.Parameters.AddWithValue("key", key);
        var value = (string?)await status.ExecuteScalarAsync(ct) ?? throw new InvalidOperationException("Buchungsperiode konnte nicht geladen werden.");
        if (value is "locked" or "closing") throw new InvalidOperationException($"Buchungsperiode {key} ist {value} und nimmt keine neuen Buchungen an.");
    }

    private static async Task<string> NextNumberAsync(NpgsqlConnection connection, NpgsqlTransaction tx, int year, CancellationToken ct)
    {
        await using var command = new NpgsqlCommand("SELECT next_backoffice_number('journal',@year,'BU',8)", connection, tx);
        command.Parameters.AddWithValue("year", year);
        return (string)(await command.ExecuteScalarAsync(ct) ?? throw new InvalidOperationException("Buchungsnummer konnte nicht vergeben werden."));
    }

    private static async Task AppendAuditAsync(NpgsqlConnection connection, NpgsqlTransaction tx, Guid actorId, string action, string entityId, string payload, CancellationToken ct)
    {
        const string sql = @"INSERT INTO backoffice_audit_events(id,occurred_at,actor_id,action,entity_type,entity_id,entity_version,payload_hash,payload)
VALUES(@id,NOW(),@actor,@action,'Accounting',@entity_id,1,@hash,@payload::jsonb)";
        await using var command = new NpgsqlCommand(sql, connection, tx);
        command.Parameters.AddWithValue("id", Guid.NewGuid());
        command.Parameters.AddWithValue("actor", actorId.ToString());
        command.Parameters.AddWithValue("action", action);
        command.Parameters.AddWithValue("entity_id", entityId);
        command.Parameters.AddWithValue("hash", Sha256(payload));
        command.Parameters.AddWithValue("payload", payload);
        await command.ExecuteNonQueryAsync(ct);
    }

    private async Task<NpgsqlConnection> OpenAsync(CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(_connectionString)) throw new InvalidOperationException("GC_BACKOFFICE_DB ist nicht konfiguriert.");
        var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(ct);
        return connection;
    }

    private static string Sha256(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
}
