using System.Security.Cryptography;
using System.Text;
using System.Threading.RateLimiting;
using GrowCentral.Backoffice.Api;
using GrowCentral.Backoffice.Domain;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

var connectionString = Environment.GetEnvironmentVariable("GC_BACKOFFICE_DB") ?? string.Empty;
var bootstrapToken = Environment.GetEnvironmentVariable("GC_BACKOFFICE_BOOTSTRAP_TOKEN") ?? string.Empty;
var secretKey = Environment.GetEnvironmentVariable("GC_BACKOFFICE_SECRET_KEY") ?? string.Empty;
BackofficeSecretProtector? secretProtector = null;
try
{
    if (!string.IsNullOrWhiteSpace(secretKey)) secretProtector = new BackofficeSecretProtector(secretKey);
}
catch (InvalidOperationException)
{
    secretProtector = null;
}

builder.Services.AddSingleton(new PostgresBackofficeStore(connectionString));
builder.Services.AddSingleton(new PostgresBackofficeWorkflowStore(connectionString));
builder.Services.AddSingleton(new PostgresAuthStore(connectionString));
builder.Services.AddSingleton(new PostgresOperatorConfigStore(connectionString));
builder.Services.AddSingleton<BusinessDocumentService>();
builder.Services.AddSingleton<BusinessDocumentRenderer>();
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddFixedWindowLimiter("auth", policy =>
    {
        policy.PermitLimit = 10;
        policy.Window = TimeSpan.FromMinutes(1);
        policy.QueueLimit = 0;
    });
});

var app = builder.Build();
app.UseRateLimiter();

bool IsBootstrapAuthorized(HttpRequest request)
{
    if (bootstrapToken.Length < 48) return false;
    if (!request.Headers.TryGetValue("X-Backoffice-Bootstrap-Token", out var supplied)) return false;
    var left = Encoding.UTF8.GetBytes(bootstrapToken);
    var right = Encoding.UTF8.GetBytes(supplied.ToString());
    return left.Length == right.Length && CryptographicOperations.FixedTimeEquals(left, right);
}

static string? BearerToken(HttpRequest request)
{
    var value = request.Headers.Authorization.ToString();
    return value.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase) ? value[7..].Trim() : null;
}

static async Task<BackofficeActor?> ActorAsync(HttpRequest request, PostgresAuthStore auth, CancellationToken ct)
{
    var token = BearerToken(request);
    return token is null ? null : await auth.AuthenticateSessionAsync(token, ct);
}

app.MapGet("/api/backoffice/health", async (PostgresBackofficeStore store, PostgresAuthStore auth, CancellationToken ct) =>
{
    var dbOk = await store.CanConnectAsync(ct);
    var hasUsers = dbOk && await auth.HasUsersAsync(ct);
    return Results.Ok(new
    {
        ok = dbOk,
        service = "GrowCentral Backoffice API",
        version = "0.5.0",
        database_configured = store.IsConfigured,
        database_reachable = dbOk,
        owner_initialized = hasUsers,
        mfa_secret_protection_ready = secretProtector is not null,
        auth_mode = "server-session+totp-mfa+rbac",
        production_auth_ready = dbOk && hasUsers && secretProtector is not null
    });
});

app.MapPost("/api/backoffice/auth/bootstrap/enroll", async (HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
{
    if (!IsBootstrapAuthorized(request)) return Results.Unauthorized();
    if (secretProtector is null) return Results.Problem("GC_BACKOFFICE_SECRET_KEY ist nicht sicher konfiguriert.", statusCode: 503);
    if (await auth.HasUsersAsync(ct)) return Results.Conflict(new { error = "Backoffice wurde bereits initialisiert." });
    var secret = BackofficeTotp.GenerateSecret();
    return Results.Ok(new { secret, otpauth_uri = BackofficeTotp.BuildOtpAuthUri(secret, "owner") });
}).RequireRateLimiting("auth");

app.MapPost("/api/backoffice/auth/bootstrap", async (HttpRequest request, BootstrapOwnerRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
{
    if (!IsBootstrapAuthorized(request)) return Results.Unauthorized();
    if (secretProtector is null) return Results.Problem("GC_BACKOFFICE_SECRET_KEY ist nicht sicher konfiguriert.", statusCode: 503);
    if (await auth.HasUsersAsync(ct)) return Results.Conflict(new { error = "Backoffice wurde bereits initialisiert." });
    try
    {
        if (string.IsNullOrWhiteSpace(payload.Username) || payload.Username.Trim().Length is < 3 or > 64)
            return Results.BadRequest(new { error = "Benutzername muss 3 bis 64 Zeichen lang sein." });
        BackofficePasswordHasher.ValidatePassword(payload.Password);
        if (!BackofficeTotp.Validate(payload.TotpSecret, payload.TotpCode, DateTimeOffset.UtcNow))
            return Results.BadRequest(new { error = "TOTP-Code ist ungültig." });
        var user = await auth.BootstrapOwnerAsync(payload.Username, BackofficePasswordHasher.Hash(payload.Password), secretProtector.Protect(payload.TotpSecret), ct);
        return Results.Created("/api/backoffice/auth/me", new { user_id = user.Id, user.Username, role = user.Role, mfa_enabled = true });
    }
    catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or CryptographicException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
}).RequireRateLimiting("auth");

app.MapPost("/api/backoffice/auth/login", async (HttpContext context, LoginRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
{
    if (secretProtector is null) return Results.Problem("Backoffice-Secret-Schutz ist nicht konfiguriert.", statusCode: 503);
    var user = await auth.FindByUsernameAsync(payload.Username, ct);
    if (user is null || !user.Enabled || !user.MfaEnabled || user.TotpSecret is null || !BackofficePasswordHasher.Verify(payload.Password, user.PasswordHash))
        return Results.Unauthorized();
    string secret;
    try { secret = secretProtector.Unprotect(user.TotpSecret); }
    catch (Exception ex) when (ex is CryptographicException or FormatException) { return Results.Problem("MFA-Secret kann nicht entschlüsselt werden.", statusCode: 503); }
    if (!BackofficeTotp.Validate(secret, payload.TotpCode, DateTimeOffset.UtcNow)) return Results.Unauthorized();
    var session = await auth.CreateSessionAsync(user, context.Connection.RemoteIpAddress?.ToString(), ct);
    return Results.Ok(new { access_token = session.Token, token_type = "Bearer", expires_at = session.ExpiresAt, user = new { user.Id, user.Username, user.Role } });
}).RequireRateLimiting("auth");

app.MapPost("/api/backoffice/auth/logout", async (HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
{
    var token = BearerToken(request);
    if (token is null) return Results.Unauthorized();
    var actor = await auth.AuthenticateSessionAsync(token, ct);
    if (actor is null) return Results.Unauthorized();
    await auth.RevokeSessionAsync(token, actor.UserId, ct);
    return Results.NoContent();
});

app.MapGet("/api/backoffice/auth/me", async (HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    return actor is null ? Results.Unauthorized() : Results.Ok(actor);
});

app.MapPost("/api/backoffice/users", async (HttpRequest request, CreateUserRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null) return Results.Unauthorized();
    if (!BackofficeRoles.CanManageUsers(actor.Role)) return Results.Forbid();
    if (secretProtector is null) return Results.Problem("Backoffice-Secret-Schutz ist nicht konfiguriert.", statusCode: 503);
    try
    {
        if (string.IsNullOrWhiteSpace(payload.Username) || payload.Username.Trim().Length is < 3 or > 64)
            return Results.BadRequest(new { error = "Benutzername muss 3 bis 64 Zeichen lang sein." });
        BackofficePasswordHasher.ValidatePassword(payload.Password);
        if (!BackofficeRoles.All.Contains(payload.Role)) return Results.BadRequest(new { error = "Ungültige Rolle." });
        var secret = BackofficeTotp.GenerateSecret();
        var user = await auth.CreateUserAsync(payload.Username, BackofficePasswordHasher.Hash(payload.Password), payload.Role, secretProtector.Protect(secret), actor.UserId, ct);
        return Results.Created($"/api/backoffice/users/{user.Id}", new
        {
            user_id = user.Id,
            user.Username,
            user.Role,
            mfa_secret = secret,
            otpauth_uri = BackofficeTotp.BuildOtpAuthUri(secret, user.Username),
            note = "MFA-Secret wird nur bei der Benutzeranlage ausgegeben. Sicher an den Benutzer übergeben."
        });
    }
    catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapPost("/api/backoffice/operator-config/validate", async (HttpRequest request, OperatorConfig payload, PostgresAuthStore auth, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
    return Results.Ok(OperatorConfigPolicy.Validate(payload));
});

app.MapGet("/api/backoffice/operator-config", async (HttpRequest request, PostgresAuthStore auth, PostgresOperatorConfigStore store, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
    var config = await store.GetAsync(ct);
    return config is null ? Results.NotFound(new { error = "Betreiber-/Steuerkonfiguration wurde noch nicht angelegt." }) : Results.Ok(new { config, validation = OperatorConfigPolicy.Validate(config) });
});

app.MapPut("/api/backoffice/operator-config", async (HttpRequest request, OperatorConfig payload, PostgresAuthStore auth, PostgresOperatorConfigStore store, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null) return Results.Unauthorized();
    if (!BackofficeRoles.CanConfigure(actor.Role)) return Results.Forbid();
    var validation = OperatorConfigPolicy.Validate(payload);
    if (!validation.IsValid) return Results.BadRequest(validation);
    try
    {
        await store.SaveAsync(payload with { LegalForm = "sole_proprietor" }, actor.UserId, ct);
        return Results.Ok(new { saved = true, validation });
    }
    catch (ArgumentException ex)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapGet("/api/backoffice/document-types", async (HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
    return Results.Ok(BusinessDocumentCatalog.All.Values.Select(x => new
    {
        x.Code,
        kind = x.Kind.ToString(),
        category = x.Category.ToString(),
        x.Title,
        allowed_parties = x.AllowedParties.Select(p => p.ToString()),
        x.LegalReviewRequired,
        x.AccountingRelevant,
        x.ImmutableAfterFinalization,
        x.LegalReference,
        number_sequence = BusinessDocumentSequenceCatalog.Get(x.Code),
        fields = x.Fields
    }));
});

app.MapPost("/api/backoffice/invoice-compliance", async (HttpRequest request, InvoiceComplianceRequest payload, PostgresAuthStore auth, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
    return Results.Ok(GermanEInvoicePolicy.Evaluate(payload.ToDomain()));
});

app.MapPost("/api/backoffice/documents/validate", async (HttpRequest request, ValidateDocumentRequest payload, PostgresAuthStore auth, BusinessDocumentService service, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
    try
    {
        var document = payload.ToDomain(actor.UserId.ToString());
        return Results.Ok(service.ValidateForFinalization(document, payload.InvoiceCompliance?.ToDomain()));
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapPost("/api/backoffice/documents", async (HttpRequest request, CreateDocumentRequest payload, PostgresAuthStore auth, PostgresBackofficeStore store, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null) return Results.Unauthorized();
    if (!BackofficeRoles.CanWriteDocuments(actor.Role)) return Results.Forbid();
    if (!store.IsConfigured) return Results.Problem("Backoffice PostgreSQL ist nicht konfiguriert.", statusCode: 503);
    try
    {
        _ = BusinessDocumentCatalog.Get(payload.TemplateCode);
        var sequence = BusinessDocumentSequenceCatalog.Get(payload.TemplateCode);
        if (!Enum.TryParse<PartyType>(payload.PartyType, true, out var partyType)) return Results.BadRequest(new { error = "Ungültiger party_type." });
        var year = payload.DocumentYear ?? DateTime.UtcNow.Year;
        if (year is < 2000 or > 2200) return Results.BadRequest(new { error = "Ungültiges Dokumentjahr." });
        var number = await store.NextDocumentNumberAsync(sequence.SequenceKey, year, sequence.Prefix, sequence.Padding, ct);
        var stored = await store.CreateDraftAsync(payload.TemplateCode, partyType, payload.PartyId, actor.UserId.ToString(), number, payload.Values, request.Headers["Idempotency-Key"].FirstOrDefault(), ct);
        return Results.Created($"/api/backoffice/documents/{stored.Id}", stored);
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapGet("/api/backoffice/documents/{id:guid}", async (Guid id, HttpRequest request, PostgresAuthStore auth, PostgresBackofficeStore store, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
    if (!store.IsConfigured) return Results.Problem("Backoffice PostgreSQL ist nicht konfiguriert.", statusCode: 503);
    var document = await store.GetAsync(id, ct);
    return document is null ? Results.NotFound() : Results.Ok(document);
});

app.MapPost("/api/backoffice/documents/{id:guid}/approve", async (Guid id, HttpRequest request, ApproveDocumentRequest payload, PostgresAuthStore auth, PostgresBackofficeStore store, PostgresBackofficeWorkflowStore workflow, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null) return Results.Unauthorized();
    if (!BackofficeRoles.CanApprove(actor.Role)) return Results.Forbid();
    if (string.IsNullOrWhiteSpace(payload.Reason)) return Results.BadRequest(new { error = "Eine nachvollziehbare Freigabebegründung ist erforderlich." });
    try
    {
        var stored = await store.GetAsync(id, ct);
        if (stored is null) return Results.NotFound();
        var definition = BusinessDocumentCatalog.Get(stored.TemplateCode);
        if (!definition.LegalReviewRequired) return Results.BadRequest(new { error = "Dieser Dokumenttyp benötigt keine gesonderte fachlich/rechtliche Freigabe." });
        var newVersion = await workflow.ApproveAsync(id, stored.Version, actor.UserId.ToString(), payload.Reason, request.Headers["Idempotency-Key"].FirstOrDefault(), ct);
        return Results.Ok(new { id, status = "Approved", version = newVersion, approved_by = actor.UserId });
    }
    catch (InvalidOperationException ex)
    {
        return Results.Conflict(new { error = ex.Message });
    }
});

app.MapPost("/api/backoffice/documents/{id:guid}/finalize", async (Guid id, HttpRequest request, FinalizeDocumentRequest payload, PostgresAuthStore auth, PostgresBackofficeStore store, BusinessDocumentService service, BusinessDocumentRenderer renderer, CancellationToken ct) =>
{
    var actor = await ActorAsync(request, auth, ct);
    if (actor is null) return Results.Unauthorized();
    if (!BackofficeRoles.CanWriteDocuments(actor.Role)) return Results.Forbid();
    try
    {
        var stored = await store.GetAsync(id, ct);
        if (stored is null) return Results.NotFound();
        if (stored.Status is not (BusinessDocumentStatus.Draft or BusinessDocumentStatus.Approved)) return Results.Conflict(new { error = $"Dokumentstatus {stored.Status} ist nicht finalisierbar." });
        var document = Rehydrate(stored);
        if (stored.Status == BusinessDocumentStatus.Approved) document.Approve();
        service.Finalize(document, actor.UserId.ToString(), payload.InvoiceCompliance?.ToDomain());
        var output = BusinessDocumentOutputPolicy.Prepare(document, renderer.Render(document, payload.GlobalValues));
        if (output.BlockingMissingValues.Count > 0) return Results.BadRequest(new { error = "Textmaster enthält ungelöste Pflichtwerte.", missing = output.BlockingMissingValues });
        document.Values.TryGetValue("e_invoice_format", out var format);
        await store.FinalizeAsync(stored, document, actor.UserId.ToString(), output.LegalTextVersion, output.Subject, output.Body, format, request.Headers["Idempotency-Key"].FirstOrDefault(), ct);
        return Results.Ok(new { id, status = "Finalized", document_number = stored.Number, optional_empty_fields = output.OptionalMissingValues });
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.Run();

static BusinessDocument Rehydrate(StoredBusinessDocument stored)
{
    var document = new BusinessDocument { Id = stored.Id, TemplateCode = stored.TemplateCode, Number = stored.Number, PartyType = stored.PartyType, CreatedBy = stored.CreatedBy, CreatedAtUtc = stored.CreatedAtUtc };
    foreach (var pair in stored.Values) document.SetValue(pair.Key, pair.Value);
    return document;
}

public sealed record BootstrapOwnerRequest(string Username, string Password, string TotpSecret, string TotpCode);
public sealed record LoginRequest(string Username, string Password, string TotpCode);
public sealed record CreateUserRequest(string Username, string Password, string Role);

public sealed record InvoiceComplianceRequest(DateOnly SupplyDate, bool SupplierEstablishedInGermany, bool CustomerEstablishedInGermany, decimal SupplierPriorYearTurnover, bool IsB2B, bool IsB2G = false, bool IsSmallAmountInvoice = false, bool IsExemptTransaction = false)
{
    public InvoiceComplianceContext ToDomain() => new(SupplyDate, SupplierEstablishedInGermany, CustomerEstablishedInGermany, SupplierPriorYearTurnover, IsB2B, IsB2G, IsSmallAmountInvoice, IsExemptTransaction);
}

public sealed record ValidateDocumentRequest(string TemplateCode, string Number, string PartyType, Dictionary<string, string?> Values, bool Approved = false, InvoiceComplianceRequest? InvoiceCompliance = null)
{
    public BusinessDocument ToDomain(string actor)
    {
        if (!Enum.TryParse<PartyType>(PartyType, true, out var partyType)) throw new ArgumentException("Ungültiger party_type.");
        var document = new BusinessDocument { TemplateCode = TemplateCode, Number = Number, PartyType = partyType, CreatedBy = actor };
        foreach (var pair in Values) document.SetValue(pair.Key, pair.Value);
        if (Approved) document.Approve();
        return document;
    }
}

public sealed record CreateDocumentRequest(string TemplateCode, string PartyType, Guid? PartyId, int? DocumentYear, Dictionary<string, string?> Values);
public sealed record ApproveDocumentRequest(string Reason);
public sealed record FinalizeDocumentRequest(InvoiceComplianceRequest? InvoiceCompliance, Dictionary<string, string?>? GlobalValues);
