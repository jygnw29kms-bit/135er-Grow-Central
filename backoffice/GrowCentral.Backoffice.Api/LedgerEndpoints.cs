using GrowCentral.Backoffice.Domain;

namespace GrowCentral.Backoffice.Api;

public static class LedgerEndpoints
{
    public static void MapLedgerEndpoints(this WebApplication app)
    {
        app.MapPost("/api/backoffice/ledger/accounts", async (HttpRequest request, LedgerAccount payload, PostgresAuthStore auth, PostgresLedgerStore ledger, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null) return Results.Unauthorized();
            if (!BackofficeRoles.CanConfigure(actor.Role)) return Results.Forbid();
            try
            {
                await ledger.CreateAccountAsync(payload, actor.UserId, ct);
                return Results.Created($"/api/backoffice/ledger/accounts/{Uri.EscapeDataString(payload.AccountNumber)}", payload);
            }
            catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
            {
                return Results.BadRequest(new { error = ex.Message });
            }
        });

        app.MapPost("/api/backoffice/ledger/validate", async (HttpRequest request, JournalEntryDraft payload, PostgresAuthStore auth, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null || !BackofficeRoles.CanRead(actor.Role)) return Results.Unauthorized();
            var accounting = DoubleEntryLedgerPolicy.Validate(payload);
            var scope = GrowCentralContractBillingLedgerPolicy.ValidateScope(payload);
            return Results.Ok(new
            {
                is_valid = accounting.IsValid && scope.Count == 0,
                accounting_errors = accounting.Errors,
                scope_errors = scope,
                debit_total = accounting.DebitTotal,
                credit_total = accounting.CreditTotal
            });
        });

        app.MapPost("/api/backoffice/ledger/entries", async (HttpRequest request, JournalEntryDraft payload, PostgresAuthStore auth, PostgresLedgerStore ledger, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null) return Results.Unauthorized();
            if (!BackofficeRoles.CanWriteDocuments(actor.Role)) return Results.Forbid();
            try
            {
                var entry = await ledger.PostAsync(payload, actor.UserId, ct);
                return Results.Created($"/api/backoffice/ledger/entries/{entry.Id}", entry);
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(new { error = ex.Message });
            }
            catch (InvalidOperationException ex)
            {
                return Results.Conflict(new { error = ex.Message });
            }
        });

        app.MapPost("/api/backoffice/ledger/periods/{periodKey}/lock", async (string periodKey, HttpRequest request, PostgresAuthStore auth, PostgresLedgerStore ledger, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null) return Results.Unauthorized();
            if (!BackofficeRoles.CanConfigure(actor.Role)) return Results.Forbid();
            try
            {
                await ledger.LockPeriodAsync(periodKey, actor.UserId, ct);
                return Results.Ok(new { period = periodKey, status = "locked" });
            }
            catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
            {
                return Results.Conflict(new { error = ex.Message });
            }
        });

        app.MapPost("/api/backoffice/ledger/periods/{periodKey}/reopen", async (string periodKey, HttpRequest request, ReopenPeriodRequest payload, PostgresAuthStore auth, PostgresLedgerStore ledger, CancellationToken ct) =>
        {
            var actor = await AuthenticateAsync(request, auth, ct);
            if (actor is null) return Results.Unauthorized();
            if (!BackofficeRoles.CanConfigure(actor.Role)) return Results.Forbid();
            try
            {
                await ledger.ReopenPeriodAsync(periodKey, payload.Reason, actor.UserId, ct);
                return Results.Ok(new { period = periodKey, status = "reopened", reason = payload.Reason });
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(new { error = ex.Message });
            }
            catch (InvalidOperationException ex)
            {
                return Results.Conflict(new { error = ex.Message });
            }
        });

        app.MapAuthHardeningEndpoints();
    }

    private static async Task<BackofficeActor?> AuthenticateAsync(HttpRequest request, PostgresAuthStore auth, CancellationToken ct)
    {
        var value = request.Headers.Authorization.ToString();
        if (!value.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase)) return null;
        return await auth.AuthenticateSessionAsync(value[7..].Trim(), ct);
    }
}

public sealed record ReopenPeriodRequest(string Reason);
