using System.Security.Cryptography;

namespace GrowCentral.Backoffice.Api;

public static class AuthHardeningEndpoints
{
    public static void MapAuthHardeningEndpoints(this WebApplication app)
    {
        BackofficeSecretProtector? protector = null;
        var secretKey = Environment.GetEnvironmentVariable("GC_BACKOFFICE_SECRET_KEY") ?? string.Empty;
        try { if (!string.IsNullOrWhiteSpace(secretKey)) protector = new BackofficeSecretProtector(secretKey); }
        catch (InvalidOperationException) { protector = null; }

        app.MapPost("/api/backoffice/auth/enroll/confirm", async (MfaEnrollmentConfirmRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
        {
            if (protector is null) return Results.Problem("Backoffice-Secret-Schutz ist nicht konfiguriert.", statusCode: 503);
            var user = await auth.FindByUsernameAsync(payload.Username, ct);
            if (user is null || !user.Enabled || user.MfaEnabled || user.TotpSecret is null || !BackofficePasswordHasher.Verify(payload.Password, user.PasswordHash))
                return Results.Unauthorized();
            string secret;
            try { secret = protector.Unprotect(user.TotpSecret); }
            catch (Exception ex) when (ex is CryptographicException or FormatException) { return Results.Problem("MFA-Secret kann nicht entschlüsselt werden.", statusCode: 503); }
            if (!BackofficeTotp.Validate(secret, payload.TotpCode, DateTimeOffset.UtcNow)) return Results.Unauthorized();
            try
            {
                await auth.ConfirmMfaEnrollmentAsync(user.Id, ct);
                return Results.Ok(new { confirmed = true, user_id = user.Id, user.Username, user.Role });
            }
            catch (InvalidOperationException ex)
            {
                return Results.Conflict(new { error = ex.Message });
            }
        }).RequireRateLimiting("auth");

        app.MapPost("/api/backoffice/auth/session", async (HttpContext context, LoginRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
        {
            if (protector is null) return Results.Problem("Backoffice-Secret-Schutz ist nicht konfiguriert.", statusCode: 503);
            var user = await auth.FindByUsernameAsync(payload.Username, ct);
            if (user is null || !user.Enabled || !user.MfaEnabled || user.TotpSecret is null || !BackofficePasswordHasher.Verify(payload.Password, user.PasswordHash))
                return Results.Unauthorized();
            string secret;
            try { secret = protector.Unprotect(user.TotpSecret); }
            catch (Exception ex) when (ex is CryptographicException or FormatException) { return Results.Problem("MFA-Secret kann nicht entschlüsselt werden.", statusCode: 503); }
            if (!BackofficeTotp.Validate(secret, payload.TotpCode, DateTimeOffset.UtcNow)) return Results.Unauthorized();
            var tokens = await auth.CreateSessionAsync(user, context.Connection.RemoteIpAddress?.ToString(), ct);
            return Results.Ok(new
            {
                access_token = tokens.AccessToken,
                access_expires_at = tokens.AccessExpiresAt,
                refresh_token = tokens.RefreshToken,
                refresh_expires_at = tokens.RefreshExpiresAt,
                token_type = "Bearer",
                user = new { user.Id, user.Username, user.Role }
            });
        }).RequireRateLimiting("auth");

        app.MapPost("/api/backoffice/auth/refresh", async (HttpContext context, RefreshSessionRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
        {
            var tokens = await auth.RotateRefreshTokenAsync(payload.RefreshToken, context.Connection.RemoteIpAddress?.ToString(), ct);
            return tokens is null
                ? Results.Unauthorized()
                : Results.Ok(new
                {
                    access_token = tokens.AccessToken,
                    access_expires_at = tokens.AccessExpiresAt,
                    refresh_token = tokens.RefreshToken,
                    refresh_expires_at = tokens.RefreshExpiresAt,
                    token_type = "Bearer"
                });
        }).RequireRateLimiting("auth");
    }
}

public sealed record MfaEnrollmentConfirmRequest(string Username, string Password, string TotpCode);
public sealed record RefreshSessionRequest(string RefreshToken);
