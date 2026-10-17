using System.Security.Cryptography;
using System.Text;
using Npgsql;

namespace GrowCentral.Backoffice.Api;

public sealed class PostgresBackofficeWorkflowStore(string connectionString)
{
    private readonly string _connectionString = connectionString;

    public async Task<int> ApproveAsync(
        Guid documentId,
        int expectedVersion,
        string actor,
        string reason,
        string? idempotencyKey,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(_connectionString))
            throw new InvalidOperationException("GC_BACKOFFICE_DB ist nicht konfiguriert.");
        ArgumentException.ThrowIfNullOrWhiteSpace(actor);
        ArgumentException.ThrowIfNullOrWhiteSpace(reason);

        var requestHash = Sha256($"approve\n{documentId}\n{expectedVersion}\n{reason.Trim()}");
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var tx = await connection.BeginTransactionAsync(cancellationToken);

        if (!string.IsNullOrWhiteSpace(idempotencyKey))
        {
            await using var reservation = new NpgsqlCommand(
                """INSERT INTO backoffice_idempotency(idempotency_key,operation,request_hash,created_at,expires_at)
                   VALUES(@key,'document.approve',@hash,NOW(),NOW()+INTERVAL '24 hours')
                   ON CONFLICT (idempotency_key) DO NOTHING""", connection, tx);
            reservation.Parameters.AddWithValue("key", idempotencyKey);
            reservation.Parameters.AddWithValue("hash", requestHash);
            if (await reservation.ExecuteNonQueryAsync(cancellationToken) == 0)
                throw new InvalidOperationException("Idempotency-Key wurde bereits verwendet.");
        }

        var newVersion = expectedVersion + 1;
        await using (var update = new NpgsqlCommand(
            """UPDATE backoffice_documents
               SET status='Approved', version=@new_version
               WHERE id=@id AND version=@expected_version AND status IN ('Draft','ReviewRequired')""", connection, tx))
        {
            update.Parameters.AddWithValue("new_version", newVersion);
            update.Parameters.AddWithValue("id", documentId);
            update.Parameters.AddWithValue("expected_version", expectedVersion);
            if (await update.ExecuteNonQueryAsync(cancellationToken) != 1)
                throw new InvalidOperationException("Dokument wurde parallel geändert oder ist nicht freigabefähig.");
        }

        await using (var audit = new NpgsqlCommand(
            """INSERT INTO backoffice_audit_events
               (id,occurred_at,actor_id,action,entity_type,entity_id,entity_version,reason,idempotency_key,payload_hash)
               VALUES(@audit_id,NOW(),@actor,'Approved','BusinessDocument',@entity_id,@version,@reason,@idempotency,@hash)""", connection, tx))
        {
            audit.Parameters.AddWithValue("audit_id", Guid.NewGuid());
            audit.Parameters.AddWithValue("actor", actor);
            audit.Parameters.AddWithValue("entity_id", documentId.ToString());
            audit.Parameters.AddWithValue("version", newVersion);
            audit.Parameters.AddWithValue("reason", reason.Trim());
            audit.Parameters.AddWithValue("idempotency", idempotencyKey is null ? DBNull.Value : idempotencyKey);
            audit.Parameters.AddWithValue("hash", requestHash);
            await audit.ExecuteNonQueryAsync(cancellationToken);
        }

        await tx.CommitAsync(cancellationToken);
        return newVersion;
    }

    private static string Sha256(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
}
