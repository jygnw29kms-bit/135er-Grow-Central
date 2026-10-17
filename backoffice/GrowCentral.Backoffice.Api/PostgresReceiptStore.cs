using System.Security.Cryptography;
using Npgsql;

namespace GrowCentral.Backoffice.Api;

public sealed record StoredReceipt(
    Guid Id,
    DateTimeOffset ReceivedAt,
    string OriginalFileName,
    string MediaType,
    long ByteLength,
    string Sha256,
    string StorageKey,
    string Source,
    string Status);

public sealed class PostgresReceiptStore(string connectionString, string storageRoot)
{
    private static readonly HashSet<string> AllowedMediaTypes = new(StringComparer.OrdinalIgnoreCase)
    {
        "application/pdf", "application/xml", "text/xml", "image/jpeg", "image/png"
    };
    private const long MaxBytes = 25 * 1024 * 1024;
    private readonly string _connectionString = connectionString;
    private readonly string _storageRoot = storageRoot;

    public async Task<StoredReceipt> StoreOriginalAsync(Stream input, string originalFileName, string mediaType, string source, Guid actorId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(_storageRoot)) throw new InvalidOperationException("GC_BACKOFFICE_STORAGE_ROOT ist nicht konfiguriert.");
        if (!AllowedMediaTypes.Contains(mediaType)) throw new ArgumentException("Nicht unterstützter Belegtyp. Zulässig sind PDF, XML, JPEG und PNG.");
        var cleanName = Path.GetFileName(originalFileName);
        if (string.IsNullOrWhiteSpace(cleanName) || cleanName.Length > 255) throw new ArgumentException("Ungültiger Originaldateiname.");

        var tmpDir = Path.Combine(_storageRoot, "tmp");
        Directory.CreateDirectory(tmpDir);
        var tmpPath = Path.Combine(tmpDir, Guid.NewGuid().ToString("N"));
        long length = 0;
        string hash;
        try
        {
            await using (var output = new FileStream(tmpPath, FileMode.CreateNew, FileAccess.Write, FileShare.None, 81920, FileOptions.Asynchronous | FileOptions.WriteThrough))
            using (var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256))
            {
                var buffer = new byte[81920];
                while (true)
                {
                    var read = await input.ReadAsync(buffer.AsMemory(0, buffer.Length), ct);
                    if (read == 0) break;
                    length += read;
                    if (length > MaxBytes) throw new ArgumentException("Beleg überschreitet die zulässige Größe von 25 MiB.");
                    sha.AppendData(buffer, 0, read);
                    await output.WriteAsync(buffer.AsMemory(0, read), ct);
                }
                await output.FlushAsync(ct);
                hash = Convert.ToHexString(sha.GetHashAndReset()).ToLowerInvariant();
            }
            if (length == 0) throw new ArgumentException("Leere Belegdateien werden nicht archiviert.");

            var storageKey = Path.Combine("original-receipts", hash[..2], hash).Replace('\\', '/');
            var finalPath = ResolveStorageKey(storageKey);
            Directory.CreateDirectory(Path.GetDirectoryName(finalPath)!);

            await using var connection = await OpenAsync(ct);
            await using var tx = await connection.BeginTransactionAsync(ct);
            var existing = await GetByHashAsync(connection, tx, hash, ct);
            if (existing is not null)
            {
                await tx.RollbackAsync(ct);
                File.Delete(tmpPath);
                return existing;
            }

            File.Move(tmpPath, finalPath, false);
            var id = Guid.NewGuid();
            var receivedAt = DateTimeOffset.UtcNow;
            try
            {
                const string originalSql = @"INSERT INTO backoffice_original_receipts
(id,received_at,original_file_name,media_type,byte_length,sha256,storage_key,source,created_by)
VALUES(@id,@received,@name,@media,@length,@hash,@storage,@source,@actor)";
                await using (var command = new NpgsqlCommand(originalSql, connection, tx))
                {
                    command.Parameters.AddWithValue("id", id);
                    command.Parameters.AddWithValue("received", receivedAt.UtcDateTime);
                    command.Parameters.AddWithValue("name", cleanName);
                    command.Parameters.AddWithValue("media", mediaType.ToLowerInvariant());
                    command.Parameters.AddWithValue("length", length);
                    command.Parameters.AddWithValue("hash", hash);
                    command.Parameters.AddWithValue("storage", storageKey);
                    command.Parameters.AddWithValue("source", string.IsNullOrWhiteSpace(source) ? "manual_upload" : source.Trim());
                    command.Parameters.AddWithValue("actor", actorId.ToString());
                    await command.ExecuteNonQueryAsync(ct);
                }
                const string workflowSql = @"INSERT INTO backoffice_receipt_workflow(receipt_id,status,updated_by)
VALUES(@id,'received',@actor)";
                await using (var command = new NpgsqlCommand(workflowSql, connection, tx))
                {
                    command.Parameters.AddWithValue("id", id);
                    command.Parameters.AddWithValue("actor", actorId.ToString());
                    await command.ExecuteNonQueryAsync(ct);
                }
                const string auditSql = @"INSERT INTO backoffice_audit_events(id,occurred_at,actor_id,action,entity_type,entity_id,entity_version,payload_hash,payload)
VALUES(@audit,NOW(),@actor,'ReceiptOriginalStored','Receipt',@entity,1,@hash,'{}'::jsonb)";
                await using (var command = new NpgsqlCommand(auditSql, connection, tx))
                {
                    command.Parameters.AddWithValue("audit", Guid.NewGuid());
                    command.Parameters.AddWithValue("actor", actorId.ToString());
                    command.Parameters.AddWithValue("entity", id.ToString());
                    command.Parameters.AddWithValue("hash", hash);
                    await command.ExecuteNonQueryAsync(ct);
                }
                await tx.CommitAsync(ct);
            }
            catch
            {
                await tx.RollbackAsync(ct);
                File.Delete(finalPath);
                throw;
            }
            return new(id, receivedAt, cleanName, mediaType.ToLowerInvariant(), length, hash, storageKey, source, "received");
        }
        finally
        {
            if (File.Exists(tmpPath)) File.Delete(tmpPath);
        }
    }

    public async Task<StoredReceipt?> GetAsync(Guid id, CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        const string sql = @"SELECT r.id,r.received_at,r.original_file_name,r.media_type,r.byte_length,r.sha256,r.storage_key,r.source,w.status
FROM backoffice_original_receipts r JOIN backoffice_receipt_workflow w ON w.receipt_id=r.id WHERE r.id=@id";
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("id", id);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        var received = DateTime.SpecifyKind(reader.GetDateTime(1), DateTimeKind.Utc);
        return new(reader.GetGuid(0), new DateTimeOffset(received), reader.GetString(2), reader.GetString(3), reader.GetInt64(4), reader.GetString(5), reader.GetString(6), reader.GetString(7), reader.GetString(8));
    }

    public string GetOriginalPath(StoredReceipt receipt)
    {
        var path = ResolveStorageKey(receipt.StorageKey);
        if (!File.Exists(path)) throw new FileNotFoundException("Archivierter Originalbeleg fehlt im Dateispeicher.");
        return path;
    }

    private string ResolveStorageKey(string storageKey)
    {
        var root = Path.GetFullPath(_storageRoot);
        var candidate = Path.GetFullPath(Path.Combine(root, storageKey.Replace('/', Path.DirectorySeparatorChar)));
        var prefix = root.EndsWith(Path.DirectorySeparatorChar) ? root : root + Path.DirectorySeparatorChar;
        if (!candidate.StartsWith(prefix, StringComparison.Ordinal)) throw new InvalidOperationException("Ungültiger Storage-Key.");
        return candidate;
    }

    private static async Task<StoredReceipt?> GetByHashAsync(NpgsqlConnection connection, NpgsqlTransaction tx, string hash, CancellationToken ct)
    {
        const string sql = @"SELECT r.id,r.received_at,r.original_file_name,r.media_type,r.byte_length,r.sha256,r.storage_key,r.source,w.status
FROM backoffice_original_receipts r JOIN backoffice_receipt_workflow w ON w.receipt_id=r.id WHERE r.sha256=@hash";
        await using var command = new NpgsqlCommand(sql, connection, tx);
        command.Parameters.AddWithValue("hash", hash);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        var received = DateTime.SpecifyKind(reader.GetDateTime(1), DateTimeKind.Utc);
        return new(reader.GetGuid(0), new DateTimeOffset(received), reader.GetString(2), reader.GetString(3), reader.GetInt64(4), reader.GetString(5), reader.GetString(6), reader.GetString(7), reader.GetString(8));
    }

    private async Task<NpgsqlConnection> OpenAsync(CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(_connectionString)) throw new InvalidOperationException("GC_BACKOFFICE_DB ist nicht konfiguriert.");
        var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(ct);
        return connection;
    }
}
