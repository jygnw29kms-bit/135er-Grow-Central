namespace GrowCentral.Backoffice.Api;

public static class ReceiptEndpoints
{
    public static void MapReceiptEndpoints(this WebApplication app)
    {
        var connectionString = Environment.GetEnvironmentVariable("GC_BACKOFFICE_DB") ?? string.Empty;
        var storageRoot = Environment.GetEnvironmentVariable("GC_BACKOFFICE_STORAGE_ROOT") ?? string.Empty;
        var receipts = new PostgresReceiptStore(connectionString, storageRoot);

        app.MapPost("/api/backoffice/receipts/original", async (HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null) return Results.Unauthorized();
            if (!BackofficeRoles.CanWriteDocuments(actor.Role)) return Results.Forbid();
            var originalName = request.Headers["X-Original-Filename"].FirstOrDefault();
            if (string.IsNullOrWhiteSpace(originalName)) return Results.BadRequest(new { error = "X-Original-Filename ist erforderlich." });
            var mediaType = request.ContentType?.Split(';', 2)[0].Trim();
            if (string.IsNullOrWhiteSpace(mediaType)) return Results.BadRequest(new { error = "Content-Type ist erforderlich." });
            var source = request.Headers["X-Receipt-Source"].FirstOrDefault() ?? "manual_upload";
            try
            {
                var receipt = await receipts.StoreOriginalAsync(request.Body, originalName, mediaType, source, actor.UserId, ct);
                return Results.Created($"/api/backoffice/receipts/{receipt.Id}", receipt);
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(new { error = ex.Message });
            }
            catch (InvalidOperationException ex)
            {
                return Results.Problem(ex.Message, statusCode: 503);
            }
        });

        app.MapGet("/api/backoffice/receipts/{id:guid}", async (Guid id, HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
            var receipt = await receipts.GetAsync(id, ct);
            return receipt is null ? Results.NotFound() : Results.Ok(receipt);
        });

        app.MapGet("/api/backoffice/receipts/{id:guid}/original", async (Guid id, HttpRequest request, PostgresAuthStore auth, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
            var receipt = await receipts.GetAsync(id, ct);
            if (receipt is null) return Results.NotFound();
            try
            {
                return Results.File(receipts.GetOriginalPath(receipt), receipt.MediaType, receipt.OriginalFileName, enableRangeProcessing: false);
            }
            catch (FileNotFoundException ex)
            {
                return Results.Problem(ex.Message, statusCode: 500);
            }
        });
    }

    private static async Task<BackofficeActor?> AuthenticateAsync(HttpRequest request, PostgresAuthStore auth, CancellationToken ct)
    {
        var value = request.Headers.Authorization.ToString();
        if (!value.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase)) return null;
        return await auth.AuthenticateSessionAsync(value[7..].Trim(), ct);
    }
}
