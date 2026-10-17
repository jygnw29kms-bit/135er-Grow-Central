using System.Security.Cryptography;
using System.Text;
using GrowCentral.Backoffice.Api;
using GrowCentral.Backoffice.Domain;

var builder = WebApplication.CreateBuilder(args);

var connectionString = Environment.GetEnvironmentVariable("GC_BACKOFFICE_DB") ?? string.Empty;
var adminToken = Environment.GetEnvironmentVariable("GC_BACKOFFICE_ADMIN_TOKEN") ?? string.Empty;
var actorId = Environment.GetEnvironmentVariable("GC_BACKOFFICE_ACTOR_ID") ?? "owner";

builder.Services.AddSingleton(new PostgresBackofficeStore(connectionString));
builder.Services.AddSingleton<BusinessDocumentService>();
builder.Services.AddSingleton<BusinessDocumentRenderer>();

var app = builder.Build();

bool IsAuthorized(HttpRequest request)
{
    if (adminToken.Length < 32) return false;
    if (!request.Headers.TryGetValue("X-Backoffice-Token", out var supplied)) return false;
    var left = Encoding.UTF8.GetBytes(adminToken);
    var right = Encoding.UTF8.GetBytes(supplied.ToString());
    return left.Length == right.Length && CryptographicOperations.FixedTimeEquals(left, right);
}

IResult RequireAuth(HttpRequest request)
    => IsAuthorized(request) ? Results.Ok() : Results.Unauthorized();

app.MapGet("/api/backoffice/health", async (HttpRequest request, PostgresBackofficeStore store, CancellationToken ct) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
    var dbOk = await store.CanConnectAsync(ct);
    return Results.Ok(new
    {
        ok = dbOk,
        service = "GrowCentral Backoffice API",
        version = "0.1.0",
        database_configured = store.IsConfigured,
        database_reachable = dbOk,
        auth_mode = "bootstrap-admin-token",
        production_auth_ready = false
    });
});

app.MapGet("/api/backoffice/document-types", (HttpRequest request) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
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
        fields = x.Fields
    }));
});

app.MapPost("/api/backoffice/invoice-compliance", (HttpRequest request, InvoiceComplianceRequest payload) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
    var decision = GermanEInvoicePolicy.Evaluate(payload.ToDomain());
    return Results.Ok(decision);
});

app.MapPost("/api/backoffice/documents/validate", (
    HttpRequest request,
    ValidateDocumentRequest payload,
    BusinessDocumentService service) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
    try
    {
        var document = payload.ToDomain(actorId);
        var result = service.ValidateForFinalization(document, payload.InvoiceCompliance?.ToDomain());
        return Results.Ok(result);
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapPost("/api/backoffice/documents", async (
    HttpRequest request,
    CreateDocumentRequest payload,
    PostgresBackofficeStore store,
    CancellationToken ct) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
    if (!store.IsConfigured) return Results.Problem("Backoffice PostgreSQL ist nicht konfiguriert.", statusCode: 503);

    try
    {
        _ = BusinessDocumentCatalog.Get(payload.TemplateCode);
        if (!Enum.TryParse<PartyType>(payload.PartyType, true, out var partyType))
            return Results.BadRequest(new { error = "Ungültiger party_type." });
        if (string.IsNullOrWhiteSpace(payload.SequenceKey) || string.IsNullOrWhiteSpace(payload.Prefix))
            return Results.BadRequest(new { error = "Nummernkreis und Präfix fehlen." });

        var year = payload.Year ?? DateTime.UtcNow.Year;
        var number = await store.NextDocumentNumberAsync(payload.SequenceKey, year, payload.Prefix, payload.Padding, ct);
        var idempotencyKey = request.Headers["Idempotency-Key"].FirstOrDefault();
        var stored = await store.CreateDraftAsync(
            payload.TemplateCode,
            partyType,
            payload.PartyId,
            actorId,
            number,
            payload.Values,
            idempotencyKey,
            ct);
        return Results.Created($"/api/backoffice/documents/{stored.Id}", stored);
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapGet("/api/backoffice/documents/{id:guid}", async (
    Guid id,
    HttpRequest request,
    PostgresBackofficeStore store,
    CancellationToken ct) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
    if (!store.IsConfigured) return Results.Problem("Backoffice PostgreSQL ist nicht konfiguriert.", statusCode: 503);
    var document = await store.GetAsync(id, ct);
    return document is null ? Results.NotFound() : Results.Ok(document);
});

app.MapPost("/api/backoffice/documents/{id:guid}/finalize", async (
    Guid id,
    HttpRequest request,
    FinalizeDocumentRequest payload,
    PostgresBackofficeStore store,
    BusinessDocumentService service,
    BusinessDocumentRenderer renderer,
    CancellationToken ct) =>
{
    if (!IsAuthorized(request)) return Results.Unauthorized();
    if (!store.IsConfigured) return Results.Problem("Backoffice PostgreSQL ist nicht konfiguriert.", statusCode: 503);

    try
    {
        var stored = await store.GetAsync(id, ct);
        if (stored is null) return Results.NotFound();
        if (stored.Status is not (BusinessDocumentStatus.Draft or BusinessDocumentStatus.Approved))
            return Results.Conflict(new { error = $"Dokumentstatus {stored.Status} ist nicht finalisierbar." });

        var document = new BusinessDocument
        {
            Id = stored.Id,
            TemplateCode = stored.TemplateCode,
            Number = stored.Number,
            PartyType = stored.PartyType,
            CreatedBy = stored.CreatedBy,
            CreatedAtUtc = stored.CreatedAtUtc
        };
        foreach (var pair in stored.Values)
            document.SetValue(pair.Key, pair.Value);
        if (stored.Status == BusinessDocumentStatus.Approved)
            document.Approve();

        service.Finalize(document, actorId, payload.InvoiceCompliance?.ToDomain());
        var rendered = renderer.Render(document, payload.GlobalValues);
        if (rendered.MissingValues.Count > 0)
            return Results.BadRequest(new { error = "Textmaster enthält ungelöste Pflicht-/Ausgabewerte.", missing = rendered.MissingValues });

        stored.Values.TryGetValue("e_invoice_format", out var format);
        var idempotencyKey = request.Headers["Idempotency-Key"].FirstOrDefault();
        await store.FinalizeAsync(
            stored,
            document,
            actorId,
            rendered.LegalTextVersion,
            rendered.Subject,
            rendered.Body,
            format,
            idempotencyKey,
            ct);
        return Results.Ok(new { id, status = "Finalized", document_number = stored.Number });
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.Run();

public sealed record InvoiceComplianceRequest(
    DateOnly SupplyDate,
    bool SupplierEstablishedInGermany,
    bool CustomerEstablishedInGermany,
    decimal SupplierPriorYearTurnover,
    bool IsB2B,
    bool IsB2G = false,
    bool IsSmallAmountInvoice = false,
    bool IsExemptTransaction = false)
{
    public InvoiceComplianceContext ToDomain() => new(
        SupplyDate,
        SupplierEstablishedInGermany,
        CustomerEstablishedInGermany,
        SupplierPriorYearTurnover,
        IsB2B,
        IsB2G,
        IsSmallAmountInvoice,
        IsExemptTransaction);
}

public sealed record ValidateDocumentRequest(
    string TemplateCode,
    string Number,
    string PartyType,
    Dictionary<string, string?> Values,
    bool Approved = false,
    InvoiceComplianceRequest? InvoiceCompliance = null)
{
    public BusinessDocument ToDomain(string actor)
    {
        if (!Enum.TryParse<PartyType>(PartyType, true, out var partyType))
            throw new ArgumentException("Ungültiger party_type.");
        var document = new BusinessDocument
        {
            TemplateCode = TemplateCode,
            Number = Number,
            PartyType = partyType,
            CreatedBy = actor
        };
        foreach (var pair in Values)
            document.SetValue(pair.Key, pair.Value);
        if (Approved) document.Approve();
        return document;
    }
}

public sealed record CreateDocumentRequest(
    string TemplateCode,
    string PartyType,
    Guid? PartyId,
    string SequenceKey,
    string Prefix,
    int? Year,
    int Padding,
    Dictionary<string, string?> Values);

public sealed record FinalizeDocumentRequest(
    InvoiceComplianceRequest? InvoiceCompliance,
    Dictionary<string, string?>? GlobalValues);
