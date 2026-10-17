using Npgsql;

namespace GrowCentral.Backoffice.Api;

public sealed record BackofficeUserRecord(Guid Id, string Username, string PasswordHash, string Role, string? TotpSecret, bool MfaEnabled, bool Enabled);
public sealed record BackofficeSessionTokens(string AccessToken, DateTimeOffset AccessExpiresAt, string RefreshToken, DateTimeOffset RefreshExpiresAt)
{
    public string Token => AccessToken;
    public DateTimeOffset ExpiresAt => AccessExpiresAt;
}

public sealed class PostgresAuthStore(string connectionString)
{
    private readonly string _connectionString = connectionString;
    public bool IsConfigured => !string.IsNullOrWhiteSpace(_connectionString);

    public async Task<bool> HasUsersAsync(CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        await using var command = new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM backoffice_users)", connection);
        return (bool)(await command.ExecuteScalarAsync(ct) ?? false);
    }

    public async Task<BackofficeUserRecord?> FindByUsernameAsync(string username, CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        const string sql = "SELECT id,username,password_hash,role,totp_secret,mfa_enabled,enabled FROM backoffice_users WHERE lower(username)=lower(@username)";
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("username", username.Trim());
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        return new(reader.GetGuid(0), reader.GetString(1), reader.GetString(2), reader.GetString(3), reader.IsDBNull(4) ? null : reader.GetString(4), reader.GetBoolean(5), reader.GetBoolean(6));
    }

    public async Task<BackofficeUserRecord?> FindByIdAsync(Guid id, CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        const string sql = "SELECT id,username,password_hash,role,totp_secret,mfa_enabled,enabled FROM backoffice_users WHERE id=@id";
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("id", id);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        return new(reader.GetGuid(0), reader.GetString(1), reader.GetString(2), reader.GetString(3), reader.IsDBNull(4) ? null : reader.GetString(4), reader.GetBoolean(5), reader.GetBoolean(6));
    }

    public async Task<BackofficeUserRecord> BootstrapOwnerAsync(string username, string passwordHash, string totpSecret, CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        await using (var lockCommand = new NpgsqlCommand("LOCK TABLE backoffice_users IN EXCLUSIVE MODE", connection, tx))
            await lockCommand.ExecuteNonQueryAsync(ct);
        await using (var count = new NpgsqlCommand("SELECT COUNT(*) FROM backoffice_users", connection, tx))
            if (Convert.ToInt64(await count.ExecuteScalarAsync(ct)) != 0)
                throw new InvalidOperationException("Backoffice wurde bereits initialisiert.");

        var id = Guid.NewGuid();
        const string sql = @"INSERT INTO backoffice_users(id,username,password_hash,role,totp_secret,mfa_enabled,enabled,created_at,updated_at)
VALUES(@id,@username,@password_hash,'Owner',@totp_secret,TRUE,TRUE,NOW(),NOW())";
        await using var insert = new NpgsqlCommand(sql, connection, tx);
        insert.Parameters.AddWithValue("id", id);
        insert.Parameters.AddWithValue("username", username.Trim());
        insert.Parameters.AddWithValue("password_hash", passwordHash);
        insert.Parameters.AddWithValue("totp_secret", totpSecret);
        await insert.ExecuteNonQueryAsync(ct);
        await AppendAuthAuditAsync(connection, tx, id.ToString(), "AuthOwnerBootstrapped", id.ToString(), ct);
        await tx.CommitAsync(ct);
        return new(id, username.Trim(), passwordHash, BackofficeRoles.Owner, totpSecret, true, true);
    }

    public async Task<BackofficeSessionTokens> CreateSessionAsync(BackofficeUserRecord user, string? remoteAddress, CancellationToken ct)
    {
        var accessToken = BackofficeTotp.NewSessionToken();
        var refreshToken = BackofficeTotp.NewSessionToken();
        var accessHash = BackofficeTotp.HashToken(accessToken);
        var refreshHash = BackofficeTotp.HashToken(refreshToken);
        var accessExpiresAt = DateTimeOffset.UtcNow.AddMinutes(30);
        var refreshExpiresAt = DateTimeOffset.UtcNow.AddDays(30);
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string sql = @"INSERT INTO backoffice_sessions(id,user_id,token_hash,refresh_token_hash,created_at,expires_at,refresh_expires_at,last_seen_at,remote_address,revoked_at)
VALUES(@id,@user_id,@token_hash,@refresh_hash,NOW(),@expires_at,@refresh_expires_at,NOW(),@remote_address,NULL)";
        await using (var command = new NpgsqlCommand(sql, connection, tx))
        {
            command.Parameters.AddWithValue("id", Guid.NewGuid());
            command.Parameters.AddWithValue("user_id", user.Id);
            command.Parameters.AddWithValue("token_hash", accessHash);
            command.Parameters.AddWithValue("refresh_hash", refreshHash);
            command.Parameters.AddWithValue("expires_at", accessExpiresAt.UtcDateTime);
            command.Parameters.AddWithValue("refresh_expires_at", refreshExpiresAt.UtcDateTime);
            command.Parameters.AddWithValue("remote_address", string.IsNullOrWhiteSpace(remoteAddress) ? DBNull.Value : remoteAddress);
            await command.ExecuteNonQueryAsync(ct);
        }
        await AppendAuthAuditAsync(connection, tx, user.Id.ToString(), "AuthLoginSucceeded", user.Id.ToString(), ct);
        await tx.CommitAsync(ct);
        return new(accessToken, accessExpiresAt, refreshToken, refreshExpiresAt);
    }

    public async Task<BackofficeSessionTokens?> RotateRefreshTokenAsync(string refreshToken, string? remoteAddress, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(refreshToken)) return null;
        var suppliedHash = BackofficeTotp.HashToken(refreshToken);
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string lookup = @"SELECT s.id,u.id,u.username,u.role,u.password_hash,u.totp_secret,u.mfa_enabled,u.enabled
FROM backoffice_sessions s JOIN backoffice_users u ON u.id=s.user_id
WHERE s.refresh_token_hash=@hash AND s.revoked_at IS NULL AND s.refresh_expires_at>NOW() AND u.enabled=TRUE AND u.mfa_enabled=TRUE
FOR UPDATE OF s";
        Guid sessionId;
        BackofficeUserRecord user;
        await using (var command = new NpgsqlCommand(lookup, connection, tx))
        {
            command.Parameters.AddWithValue("hash", suppliedHash);
            await using var reader = await command.ExecuteReaderAsync(ct);
            if (!await reader.ReadAsync(ct))
            {
                await tx.RollbackAsync(ct);
                return null;
            }
            sessionId = reader.GetGuid(0);
            user = new(reader.GetGuid(1), reader.GetString(2), reader.GetString(4), reader.GetString(3), reader.IsDBNull(5) ? null : reader.GetString(5), reader.GetBoolean(6), reader.GetBoolean(7));
        }

        var accessToken = BackofficeTotp.NewSessionToken();
        var newRefreshToken = BackofficeTotp.NewSessionToken();
        var accessExpiresAt = DateTimeOffset.UtcNow.AddMinutes(30);
        var refreshExpiresAt = DateTimeOffset.UtcNow.AddDays(30);
        const string rotate = @"UPDATE backoffice_sessions
SET token_hash=@access_hash,refresh_token_hash=@refresh_hash,expires_at=@access_expires,refresh_expires_at=@refresh_expires,last_seen_at=NOW(),rotated_at=NOW(),remote_address=@remote
WHERE id=@id";
        await using (var command = new NpgsqlCommand(rotate, connection, tx))
        {
            command.Parameters.AddWithValue("access_hash", BackofficeTotp.HashToken(accessToken));
            command.Parameters.AddWithValue("refresh_hash", BackofficeTotp.HashToken(newRefreshToken));
            command.Parameters.AddWithValue("access_expires", accessExpiresAt.UtcDateTime);
            command.Parameters.AddWithValue("refresh_expires", refreshExpiresAt.UtcDateTime);
            command.Parameters.AddWithValue("remote", string.IsNullOrWhiteSpace(remoteAddress) ? DBNull.Value : remoteAddress);
            command.Parameters.AddWithValue("id", sessionId);
            await command.ExecuteNonQueryAsync(ct);
        }
        await AppendAuthAuditAsync(connection, tx, user.Id.ToString(), "AuthRefreshRotated", sessionId.ToString(), ct);
        await tx.CommitAsync(ct);
        return new(accessToken, accessExpiresAt, newRefreshToken, refreshExpiresAt);
    }

    public async Task<BackofficeActor?> AuthenticateSessionAsync(string token, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(token)) return null;
        var hash = BackofficeTotp.HashToken(token);
        await using var connection = await OpenAsync(ct);
        const string sql = @"SELECT u.id,u.username,u.role
FROM backoffice_sessions s JOIN backoffice_users u ON u.id=s.user_id
WHERE s.token_hash=@hash AND s.revoked_at IS NULL AND s.expires_at>NOW() AND u.enabled=TRUE AND u.mfa_enabled=TRUE";
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("hash", hash);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        return new(reader.GetGuid(0), reader.GetString(1), reader.GetString(2));
    }

    public async Task ConfirmMfaEnrollmentAsync(Guid userId, CancellationToken ct)
    {
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        await using (var command = new NpgsqlCommand("UPDATE backoffice_users SET mfa_enabled=TRUE,updated_at=NOW() WHERE id=@id AND enabled=TRUE AND mfa_enabled=FALSE AND totp_secret IS NOT NULL", connection, tx))
        {
            command.Parameters.AddWithValue("id", userId);
            if (await command.ExecuteNonQueryAsync(ct) != 1) throw new InvalidOperationException("MFA-Ersteinrichtung ist nicht bestätigbar.");
        }
        await AppendAuthAuditAsync(connection, tx, userId.ToString(), "AuthMfaEnrollmentConfirmed", userId.ToString(), ct);
        await tx.CommitAsync(ct);
    }

    public async Task RevokeSessionAsync(string token, Guid actorId, CancellationToken ct)
    {
        var hash = BackofficeTotp.HashToken(token);
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        await using (var command = new NpgsqlCommand("UPDATE backoffice_sessions SET revoked_at=NOW(),refresh_token_hash=NULL WHERE token_hash=@hash AND revoked_at IS NULL", connection, tx))
        {
            command.Parameters.AddWithValue("hash", hash);
            await command.ExecuteNonQueryAsync(ct);
        }
        await AppendAuthAuditAsync(connection, tx, actorId.ToString(), "AuthLogout", actorId.ToString(), ct);
        await tx.CommitAsync(ct);
    }

    public async Task<BackofficeUserRecord> CreateUserAsync(string username, string passwordHash, string role, string totpSecret, Guid actorId, CancellationToken ct)
    {
        if (!BackofficeRoles.All.Contains(role)) throw new ArgumentException("Ungültige Rolle.");
        var id = Guid.NewGuid();
        await using var connection = await OpenAsync(ct);
        await using var tx = await connection.BeginTransactionAsync(ct);
        const string sql = @"INSERT INTO backoffice_users(id,username,password_hash,role,totp_secret,mfa_enabled,enabled,created_at,updated_at)
VALUES(@id,@username,@password_hash,@role,@totp_secret,FALSE,TRUE,NOW(),NOW())";
        await using (var command = new NpgsqlCommand(sql, connection, tx))
        {
            command.Parameters.AddWithValue("id", id);
            command.Parameters.AddWithValue("username", username.Trim());
            command.Parameters.AddWithValue("password_hash", passwordHash);
            command.Parameters.AddWithValue("role", role);
            command.Parameters.AddWithValue("totp_secret", totpSecret);
            await command.ExecuteNonQueryAsync(ct);
        }
        await AppendAuthAuditAsync(connection, tx, actorId.ToString(), "AuthUserCreatedPendingMfa", id.ToString(), ct);
        await tx.CommitAsync(ct);
        return new(id, username.Trim(), passwordHash, role, totpSecret, false, true);
    }

    private async Task<NpgsqlConnection> OpenAsync(CancellationToken ct)
    {
        if (!IsConfigured) throw new InvalidOperationException("GC_BACKOFFICE_DB ist nicht konfiguriert.");
        var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(ct);
        return connection;
    }

    private static async Task AppendAuthAuditAsync(NpgsqlConnection connection, NpgsqlTransaction tx, string actor, string action, string entityId, CancellationToken ct)
    {
        const string sql = @"INSERT INTO backoffice_audit_events(id,occurred_at,actor_id,action,entity_type,entity_id,entity_version,payload_hash,payload)
VALUES(@id,NOW(),@actor,@action,'BackofficeUser',@entity_id,1,@hash,'{}'::jsonb)";
        await using var command = new NpgsqlCommand(sql, connection, tx);
        command.Parameters.AddWithValue("id", Guid.NewGuid());
        command.Parameters.AddWithValue("actor", actor);
        command.Parameters.AddWithValue("action", action);
        command.Parameters.AddWithValue("entity_id", entityId);
        command.Parameters.AddWithValue("hash", BackofficeTotp.HashToken($"{actor}:{action}:{entityId}:{DateTimeOffset.UtcNow:O}"));
        await command.ExecuteNonQueryAsync(ct);
    }
}
