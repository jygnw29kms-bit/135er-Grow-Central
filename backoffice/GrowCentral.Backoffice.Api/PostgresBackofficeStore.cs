using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using GrowCentral.Backoffice.Domain;
using Npgsql;

namespace GrowCentral.Backoffice.Api;

public sealed record StoredBusinessDocument(
    Guid Id,
    string TemplateCode,
    string Number,
    PartyType PartyType,
    BusinessDocumentStatus Status,
    int Version,
    string CreatedBy,
    DateTimeOffset CreatedAtUtc,
    IReadOnlyDictionary<string, string?> Values);

public sealed class PostgresBackofficeStore(string connectionString)
{
    private readonly string _connectionString = connectionString;

    public bool IsConfigured => !string.IsNullOrWhiteSpace(_connectionString);

    public async Task<bool> CanConnectAsync(CancellationToken cancellationToken)
    {
        if (!IsConfigured) return false;
        try
        {
            await using var connection = new NpgsqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);
            await using var command = new NpgsqlCommand("SELECT 1", connection);
            return Convert.ToInt32(await command.ExecuteScalarAsync(cancellationToken), CultureInfo.InvariantCulture) == 1;
        }
        catch (NpgsqlException)
        {
            return false;
        }
    }

    public async Task<string> NextDocumentNumberAsync(string sequenceKey, int year, string prefix, int padding, CancellationToken cancellationToken)
    {
        EnsureConfigured();
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new NpgsqlCommand("SELECT next_backoffice_number(@key,@year,@prefix,@padding)", connection);
        command.Parameters.AddWithValue("key", sequenceKey);
        command.Parameters.AddWithValue("year", year);
        command.Parameters.AddWithValue("prefix", prefix);
        command.Parameters.AddWithValue("padding", padding);
        return (string)(await command.ExecuteScalarAsync(cancellationToken)
            ?? throw new InvalidOperationException("Nummernkreis lieferte keinen Wert."));
    }

    public async Task<StoredBusinessDocument> CreateDraftAsync(
        string templateCode,
        PartyType partyType,
        Guid? partyId,
        string actor,
        string number,
        IReadOnlyDictionary<string, string?> values,
        string? idempotencyKey,
        CancellationToken cancellationToken)
    {
        EnsureConfigured();
        var id = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        var valuesJson = JsonSerializer.Serialize(values);
        var payloadHash = Sha256(valuesJson);

        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var tx = await connection.BeginTransactionAsync(cancellationToken);

        if (!string.IsNullOrWhiteSpace(idempotencyKey))
        {
            const string sql = @"INSERT INTO backoffice_idempotency(idempotency_key,operation,request_hash,created_at,expires_at)
VALUES(@key,'document.create',@hash,NOW(),NOW()+INTERVAL '24 hours')
ON CONFLICT (idempotency_key) DO NOTHING";
            await using var reservation = new NpgsqlCommand(sql, connection, tx);
            reservation.Parameters.AddWithValue("key", idempotencyKey);
            reservation.Parameters.AddWithValue("hash", payloadHash);
            if (await reservation.ExecuteNonQueryAsync(cancellationToken) == 0)
                throw new InvalidOperationException("Idempotency-Key wurde bereits verwendet.");
        }

        const string insertSql = @"INSERT INTO backoffice_documents
(id,template_code,document_number,party_type,party_id,status,version,created_at,created_by,current_values,content_hash)
VALUES(@id,@template,@number,@party_type,@party_id,'Draft',1,@created_at,@created_by,@values::jsonb,@hash)";
        await using (var insert = new NpgsqlCommand(insertSql, connection, tx))
        {
            insert.Parameters.AddWithValue("id", id);
            insert.Parameters.AddWithValue("template", templateCode);
            insert.Parameters.AddWithValue("number", number);
            insert.Parameters.AddWithValue("party_type", partyType.ToString().ToLowerInvariant());
            insert.Parameters.AddWithValue("party_id", partyId.HasValue ? partyId.Value : DBNull.Value);
            insert.Parameters.AddWithValue("created_at", now.UtcDateTime);
            insert.Parameters.AddWithValue("created_by", actor);
            insert.Parameters.AddWithValue("values", valuesJson);
            insert.Parameters.AddWithValue("hash", payloadHash);
            await insert.ExecuteNonQueryAsync(cancellationToken);
        }

        await AppendAuditAsync(connection, tx, actor, AuditAction.Created, id, 1, null, idempotencyKey, payloadHash, cancellationToken);
        await tx.CommitAsync(cancellationToken);

        return new(id, templateCode, number, partyType, BusinessDocumentStatus.Draft, 1, actor, now, values);
    }

    public async Task<StoredBusinessDocument?> GetAsync(Guid id, CancellationToken cancellationToken)
    {
        EnsureConfigured();
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        const string sql = @"SELECT id,template_code,document_number,party_type,status,version,created_by,created_at,current_values::text
FROM backoffice_documents WHERE id=@id";
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("id", id);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken)) return null;

        var values = JsonSerializer.Deserialize<Dictionary<string, string?>>(reader.GetString(8))
            ?? new Dictionary<string, string?>();
        var createdAtUtc = DateTime.SpecifyKind(reader.GetDateTime(7), DateTimeKind.Utc);
        return new(
            reader.GetGuid(0),
            reader.GetString(1),
            reader.GetString(2),
            Enum.Parse<PartyType>(reader.GetString(3), true),
            Enum.Parse<BusinessDocumentStatus>(reader.GetString(4), true),
            reader.GetInt32(5),
            reader.GetString(6),
            new DateTimeOffset(createdAtUtc),
            values);
    }

    public async Task FinalizeAsync(
        StoredBusinessDocument stored,
        BusinessDocument finalized,
        string actor,
        string legalTextVersion,
        string renderedSubject,
        string renderedBody,
        string? structuredInvoiceFormat,
        string? idempotencyKey,
        CancellationToken cancellationToken)
    {
        EnsureConfigured();
        var valuesJson = JsonSerializer.Serialize(finalized.Values);
        var hashInput = string.Concat(valuesJson, "\n", legalTextVersion, "\n", renderedSubject, "\n", renderedBody, "\n", structuredInvoiceFormat);
        var contentHash = Sha256(hashInput);
        var newVersion = stored.Version + 1;

        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var tx = await connection.BeginTransactionAsync(cancellationToken);

        if (!string.IsNullOrWhiteSpace(idempotencyKey))
        {
            const string sql = @"INSERT INTO backoffice_idempotency(idempotency_key,operation,request_hash,created_at,expires_at)
VALUES(@key,'document.finalize',@hash,NOW(),NOW()+INTERVAL '24 hours')
ON CONFLICT (idempotency_key) DO NOTHING";
            await using var reservation = new NpgsqlCommand(sql, connection, tx);
            reservation.Parameters.AddWithValue("key", idempotencyKey);
            reservation.Parameters.AddWithValue("hash", contentHash);
            if (await reservation.ExecuteNonQueryAsync(cancellationToken) == 0)
                throw new InvalidOperationException("Idempotency-Key wurde bereits verwendet.");
        }

        const string updateSql = @"UPDATE backoffice_documents
SET status='Finalized', version=@new_version, finalized_at=NOW(), finalized_by=@actor,
    current_values=@values::jsonb, content_hash=@hash
WHERE id=@id AND version=@expected_version AND status IN ('Draft','Approved')";
        await using (var update = new NpgsqlCommand(updateSql, connection, tx))
        {
            update.Parameters.AddWithValue("new_version", newVersion);
            update.Parameters.AddWithValue("actor", actor);
            update.Parameters.AddWithValue("values", valuesJson);
            update.Parameters.AddWithValue("hash", contentHash);
            update.Parameters.AddWithValue("id", stored.Id);
            update.Parameters.AddWithValue("expected_version", stored.Version);
            if (await update.ExecuteNonQueryAsync(cancellationToken) != 1)
                throw new InvalidOperationException("Dokument wurde parallel geändert oder ist nicht mehr finalisierbar.");
        }

        const string revisionSql = @"INSERT INTO backoffice_document_revisions
(id,document_id,document_version,status,values_json,links_json,text_template_version,rendered_subject,rendered_body,structured_invoice_format,content_hash,created_by)
VALUES(@revision_id,@document_id,@version,'Finalized',@values::jsonb,'[]'::jsonb,@text_version,@subject,@body,@format,@hash,@actor)";
        await using (var revision = new NpgsqlCommand(revisionSql, connection, tx))
        {
            revision.Parameters.AddWithValue("revision_id", Guid.NewGuid());
            revision.Parameters.AddWithValue("document_id", stored.Id);
            revision.Parameters.AddWithValue("version", newVersion);
            revision.Parameters.AddWithValue("values", valuesJson);
            revision.Parameters.AddWithValue("text_version", legalTextVersion);
            revision.Parameters.AddWithValue("subject", renderedSubject);
            revision.Parameters.AddWithValue("body", renderedBody);
            revision.Parameters.AddWithValue("format", structuredInvoiceFormat is null ? DBNull.Value : structuredInvoiceFormat);
            revision.Parameters.AddWithValue("hash", contentHash);
            revision.Parameters.AddWithValue("actor", actor);
            await revision.ExecuteNonQueryAsync(cancellationToken);
        }

        await AppendAuditAsync(connection, tx, actor, AuditAction.Finalized, stored.Id, newVersion, null, idempotencyKey, contentHash, cancellationToken);
        await tx.CommitAsync(cancellationToken);
    }

    private static async Task AppendAuditAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction tx,
        string actor,
        AuditAction action,
        Guid documentId,
        int version,
        string? reason,
        string? idempotencyKey,
        string payloadHash,
        CancellationToken cancellationToken)
    {
        const string sql = @"INSERT INTO backoffice_audit_events
(id,occurred_at,actor_id,action,entity_type,entity_id,entity_version,reason,idempotency_key,payload_hash)
VALUES(@id,NOW(),@actor,@action,'BusinessDocument',@entity_id,@version,@reason,@idempotency,@hash)";
        await using var audit = new NpgsqlCommand(sql, connection, tx);
        audit.Parameters.AddWithValue("id", Guid.NewGuid());
        audit.Parameters.AddWithValue("actor", actor);
        audit.Parameters.AddWithValue("action", action.ToString());
        audit.Parameters.AddWithValue("entity_id", documentId.ToString());
        audit.Parameters.AddWithValue("version", version);
        audit.Parameters.AddWithValue("reason", reason is null ? DBNull.Value : reason);
        audit.Parameters.AddWithValue("idempotency", idempotencyKey is null ? DBNull.Value : idempotencyKey);
        audit.Parameters.AddWithValue("hash", payloadHash);
        await audit.ExecuteNonQueryAsync(cancellationToken);
    }

    private void EnsureConfigured()
    {
        if (!IsConfigured)
            throw new InvalidOperationException("GC_BACKOFFICE_DB ist nicht konfiguriert.");
    }

    private static string Sha256(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
}
