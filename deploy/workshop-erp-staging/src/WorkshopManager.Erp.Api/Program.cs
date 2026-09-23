using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.IdentityModel.Tokens;
using WorkshopManager.Erp.Infrastructure.Security;
using Microsoft.EntityFrameworkCore;
using WorkshopManager.Erp.Core.Domain;
using WorkshopManager.Erp.Core.Services;
using WorkshopManager.Erp.Infrastructure.Persistence;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<ErpDbContext>(opt =>
    opt.UseNpgsql(builder.Configuration.GetConnectionString("Erp")));
builder.Services.AddScoped<WorkOrderWorkflowService>();
builder.Services.AddScoped<NumberSequenceService>();
builder.Services.AddScoped<PermissionService>();
builder.Services.AddHttpContextAccessor();
builder.Services.AddIdentityCore<ErpIdentityUser>(options =>
{
    options.Password.RequiredLength = 12;
    options.Password.RequireDigit = true;
    options.Password.RequireLowercase = true;
    options.Password.RequireUppercase = true;
    options.Password.RequireNonAlphanumeric = true;
    options.Lockout.MaxFailedAccessAttempts = 8;
})
.AddRoles<IdentityRole<Guid>>()
.AddEntityFrameworkStores<ErpDbContext>();

var jwtKey = builder.Configuration["Jwt:Key"];
if (string.IsNullOrWhiteSpace(jwtKey))
    jwtKey = Environment.GetEnvironmentVariable("WM_JWT_KEY") ?? "";
if (jwtKey.Length < 32)
    throw new InvalidOperationException("JWT-Schlüssel fehlt oder ist zu kurz. Setze Jwt:Key oder WM_JWT_KEY mit mindestens 32 Zeichen.");

var jwtIssuer = builder.Configuration["Jwt:Issuer"] ?? "workshop-manager-erp";
var jwtAudience = builder.Configuration["Jwt:Audience"] ?? "workshop-manager-clients";
var signingKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey));

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = jwtIssuer,
            ValidateAudience = true,
            ValidAudience = jwtAudience,
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = signingKey,
            ValidateLifetime = true,
            ClockSkew = TimeSpan.FromMinutes(1)
        };
    });

builder.Services.AddAuthorization(options =>
{
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
});

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

app.Use(async (http, next) =>
{
    if (!http.Request.Path.StartsWithSegments("/api") ||
        http.Request.Path.StartsWithSegments("/api/health") ||
        http.Request.Path.StartsWithSegments("/api/auth/login"))
    {
        await next();
        return;
    }

    var required = ResolvePermission(http.Request.Method, http.Request.Path);
    if (required is null)
    {
        await next();
        return;
    }

    var tenantRaw = http.User.FindFirstValue("tenant_id");
    var profileRaw = http.User.FindFirstValue("profile_id");
    var siteRaw = http.User.FindFirstValue("site_id");

    if (!Guid.TryParse(tenantRaw, out var tenantId) || !Guid.TryParse(profileRaw, out var profileId))
    {
        http.Response.StatusCode = StatusCodes.Status403Forbidden;
        return;
    }

    Guid? siteId = Guid.TryParse(siteRaw, out var parsedSite) ? parsedSite : null;
    var permissions = http.RequestServices.GetRequiredService<PermissionService>();
    if (!await permissions.HasAsync(tenantId, profileId, required, siteId, http.RequestAborted))
    {
        http.Response.StatusCode = StatusCodes.Status403Forbidden;
        return;
    }

    await next();
});

if (builder.Configuration.GetValue<bool>("DemoSeed"))
{
    using var scope = app.Services.CreateScope();
    await SeedData.EnsureDemoAsync(scope.ServiceProvider.GetRequiredService<ErpDbContext>());
}

{
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<ErpDbContext>();
    var users = scope.ServiceProvider.GetRequiredService<UserManager<ErpIdentityUser>>();
    var bootstrapName = builder.Configuration["BootstrapAdmin:Username"];
    if (string.IsNullOrWhiteSpace(bootstrapName))
        bootstrapName = Environment.GetEnvironmentVariable("WM_BOOTSTRAP_ADMIN");
    var bootstrapPassword = builder.Configuration["BootstrapAdmin:Password"];
    if (string.IsNullOrWhiteSpace(bootstrapPassword))
        bootstrapPassword = Environment.GetEnvironmentVariable("WM_BOOTSTRAP_PASSWORD");

    if (!string.IsNullOrWhiteSpace(bootstrapName) && !string.IsNullOrWhiteSpace(bootstrapPassword))
    {
        var tenantId = await db.Tenants.Select(x => x.Id).FirstAsync();
        var identity = await users.FindByNameAsync(bootstrapName);
        if (identity is null)
        {
            identity = new ErpIdentityUser
            {
                Id = Guid.NewGuid(),
                TenantId = tenantId,
                UserName = bootstrapName,
                DisplayName = "ERP Administrator",
                Active = true
            };
            var created = await users.CreateAsync(identity, bootstrapPassword);
            if (!created.Succeeded)
                throw new InvalidOperationException("Bootstrap-Admin konnte nicht angelegt werden: " + string.Join("; ", created.Errors.Select(x => x.Description)));
        }

        var profile = await db.UserProfiles.FirstOrDefaultAsync(x => x.TenantId == tenantId && x.ExternalSubject == identity.Id.ToString());
        if (profile is null)
        {
            profile = new UserProfile
            {
                TenantId = tenantId,
                ExternalSubject = identity.Id.ToString(),
                DisplayName = identity.DisplayName,
                Email = identity.Email ?? "",
                Active = true
            };
            db.UserProfiles.Add(profile);
            await db.SaveChangesAsync();
        }

        await SecuritySeed.EnsureAdminAsync(db, tenantId, profile.Id);
    }
}

app.MapGet("/api/health", () => Results.Ok(new
{
    product = "Workshop Manager ERP",
    developer = "JL 1976™",
    status = "ok",
    utc = DateTimeOffset.UtcNow
})).AllowAnonymous();

app.MapPost("/api/auth/login", async (LoginRequest req, UserManager<ErpIdentityUser> users, ErpDbContext db, CancellationToken ct) =>
{
    var user = await users.FindByNameAsync(req.Username);
    if (user is null || !user.Active || !await users.CheckPasswordAsync(user, req.Password))
        return Results.Unauthorized();

    var profile = await db.UserProfiles.AsNoTracking()
        .FirstOrDefaultAsync(x => x.TenantId == user.TenantId && x.ExternalSubject == user.Id.ToString() && x.Active && !x.IsDeleted, ct);
    if (profile is null) return Results.Unauthorized();

    var claims = new List<Claim>
    {
        new(JwtRegisteredClaimNames.Sub, user.Id.ToString()),
        new(ClaimTypes.Name, user.UserName ?? user.Id.ToString()),
        new("tenant_id", user.TenantId.ToString()),
        new("profile_id", profile.Id.ToString())
    };
    if (user.SiteId is Guid siteId) claims.Add(new("site_id", siteId.ToString()));

    var token = new JwtSecurityToken(
        issuer: jwtIssuer,
        audience: jwtAudience,
        claims: claims,
        expires: DateTime.UtcNow.AddHours(8),
        signingCredentials: new SigningCredentials(signingKey, SecurityAlgorithms.HmacSha256));

    return Results.Ok(new
    {
        access_token = new JwtSecurityTokenHandler().WriteToken(token),
        token_type = "Bearer",
        expires_in = 28800,
        user = new { user.Id, user.UserName, user.DisplayName, user.TenantId, user.SiteId, profileId = profile.Id }
    });
}).AllowAnonymous();

string? ResolvePermission(string method, PathString path)
{
    var p = path.Value?.ToLowerInvariant() ?? "";
    var write = method is "POST" or "PUT" or "PATCH" or "DELETE";

    if (p.StartsWith("/api/sites")) return "resources.read";
    if (p.StartsWith("/api/customers")) return write ? "customers.write" : "customers.read";
    if (p.StartsWith("/api/vehicles")) return write ? "vehicles.write" : "vehicles.read";
    if (p.StartsWith("/api/appointments")) return write ? "appointments.write" : "appointments.read";
    if (p.StartsWith("/api/work-orders") || p.StartsWith("/api/approvals") || p.StartsWith("/api/time")) return write ? "orders.write" : "orders.read";
    if (p.StartsWith("/api/inventory")) return write ? "inventory.write" : "inventory.read";
    if (p.StartsWith("/api/purchase-orders") || p.StartsWith("/api/suppliers")) return write ? "purchasing.write" : "purchasing.read";
    if (p.StartsWith("/api/tires")) return write ? "tires.write" : "tires.read";
    if (p.StartsWith("/api/employees") || p.StartsWith("/api/absences")) return write ? "personnel.write" : "personnel.read";
    if (p.StartsWith("/api/invoices")) return write ? "billing.write" : "billing.read";
    if (p.StartsWith("/api/resources")) return write ? "resources.write" : "resources.read";
    if (p.StartsWith("/api/reminders")) return write ? "crm.write" : "crm.read";
    if (p.StartsWith("/api/loaners")) return write ? "loaners.write" : "loaners.read";
    if (p.StartsWith("/api/reports")) return "reports.read";
    if (p.StartsWith("/api/admin")) return "admin.security";
    if (p.StartsWith("/api/dashboard")) return "reports.read";
    return null;
}

async Task<Guid> TenantId(ErpDbContext db, CancellationToken ct)
{
    var http = app.Services.GetRequiredService<IHttpContextAccessor>().HttpContext;
    var raw = http?.User.FindFirstValue("tenant_id");
    if (!Guid.TryParse(raw, out var id))
        throw new UnauthorizedAccessException("Mandant fehlt im Zugriffstoken.");

    if (!await db.Tenants.AsNoTracking().AnyAsync(x => x.Id == id && x.Active && !x.IsDeleted, ct))
        throw new UnauthorizedAccessException("Mandant ist nicht aktiv.");

    return id;
}

app.MapGet("/api/customers", async (string? q, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var query = db.Customers.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (!string.IsNullOrWhiteSpace(q))
    {
        var s = q.Trim().ToLower();
        query = query.Where(x =>
            x.DisplayName.ToLower().Contains(s) ||
            x.CompanyName.ToLower().Contains(s) ||
            x.CustomerNumber.ToLower().Contains(s) ||
            x.Phone.ToLower().Contains(s));
    }
    return Results.Ok(await query.OrderBy(x => x.DisplayName).Take(250).ToListAsync(ct));
});

app.MapPost("/api/customers", async (CustomerCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var next = await db.Customers.CountAsync(x => x.TenantId == tenantId, ct) + 10001;
    var entity = new Customer
    {
        TenantId = tenantId,
        CustomerNumber = $"K-{next}",
        DisplayName = req.DisplayName.Trim(),
        CompanyName = req.CompanyName?.Trim() ?? "",
        FirstName = req.FirstName?.Trim() ?? "",
        LastName = req.LastName?.Trim() ?? "",
        Email = req.Email?.Trim() ?? "",
        Phone = req.Phone?.Trim() ?? "",
        Mobile = req.Mobile?.Trim() ?? "",
        Street = req.Street?.Trim() ?? "",
        PostalCode = req.PostalCode?.Trim() ?? "",
        City = req.City?.Trim() ?? "",
        Notes = req.Notes?.Trim() ?? ""
    };
    db.Customers.Add(entity);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/customers/{entity.Id}", entity);
});

app.MapGet("/api/vehicles", async (string? q, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var query = db.Vehicles.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (!string.IsNullOrWhiteSpace(q))
    {
        var s = q.Trim().ToLower();
        query = query.Where(x => x.LicensePlate.ToLower().Contains(s) || x.Vin.ToLower().Contains(s) ||
                                 x.Make.ToLower().Contains(s) || x.Model.ToLower().Contains(s));
    }
    return Results.Ok(await query.OrderBy(x => x.LicensePlate).Take(250).ToListAsync(ct));
});

app.MapPost("/api/vehicles", async (VehicleCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (!await db.Customers.AnyAsync(x => x.Id == req.CustomerId && x.TenantId == tenantId, ct))
        return Results.BadRequest(new { error = "Kunde nicht gefunden." });

    var entity = new Vehicle
    {
        TenantId = tenantId,
        CustomerId = req.CustomerId,
        LicensePlate = req.LicensePlate.Trim().ToUpperInvariant(),
        Vin = req.Vin?.Trim().ToUpperInvariant() ?? "",
        Make = req.Make?.Trim() ?? "",
        Model = req.Model?.Trim() ?? "",
        Type = req.Type?.Trim() ?? "",
        Hsn = req.Hsn?.Trim() ?? "",
        Tsn = req.Tsn?.Trim() ?? "",
        FirstRegistration = req.FirstRegistration,
        Mileage = req.Mileage,
        NextHu = req.NextHu,
        NextService = req.NextService
    };
    db.Vehicles.Add(entity);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/vehicles/{entity.Id}", entity);
});

app.MapGet("/api/appointments", async (DateOnly? date, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var query = db.Appointments.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (date is not null)
    {
        var from = new DateTimeOffset(date.Value.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero);
        var to = from.AddDays(1);
        query = query.Where(x => x.StartsAt >= from && x.StartsAt < to);
    }
    return Results.Ok(await query.OrderBy(x => x.StartsAt).ToListAsync(ct));
});

app.MapPost("/api/appointments", async (AppointmentCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var siteId = req.SiteId ?? await db.Sites.Where(x => x.TenantId == tenantId).Select(x => x.Id).FirstAsync(ct);
    var entity = new Appointment
    {
        TenantId = tenantId,
        SiteId = siteId,
        CustomerId = req.CustomerId,
        VehicleId = req.VehicleId,
        ResourceId = req.ResourceId,
        EmployeeId = req.EmployeeId,
        StartsAt = req.StartsAt,
        EndsAt = req.EndsAt,
        Status = AppointmentStatus.Confirmed,
        Subject = req.Subject.Trim(),
        CustomerRequest = req.CustomerRequest?.Trim() ?? ""
    };
    db.Appointments.Add(entity);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/appointments/{entity.Id}", entity);
});

app.MapPost("/api/work-orders/from-appointment/{appointmentId:guid}", async (Guid appointmentId, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var appt = await db.Appointments.FirstOrDefaultAsync(x => x.Id == appointmentId && x.TenantId == tenantId, ct);
    if (appt is null) return Results.NotFound();
    if (appt.WorkOrderId is not null)
    {
        var existing = await db.WorkOrders.FindAsync([appt.WorkOrderId.Value], ct);
        return Results.Ok(existing);
    }

    var orderNumber = await numbers.NextAsync(tenantId, appt.SiteId, "work-order", "AU-", 5, true, ct);
    var order = new WorkOrder
    {
        TenantId = tenantId,
        SiteId = appt.SiteId,
        CustomerId = appt.CustomerId,
        VehicleId = appt.VehicleId,
        AppointmentId = appt.Id,
        Number = orderNumber,
        Status = WorkOrderStatus.Scheduled,
        CustomerRequest = appt.CustomerRequest,
        PromisedAt = appt.EndsAt
    };
    db.WorkOrders.Add(order);
    appt.WorkOrderId = order.Id;
    appt.Status = AppointmentStatus.Converted;
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/work-orders/{order.Id}", order);
});

app.MapGet("/api/work-orders", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.WorkOrders.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .OrderByDescending(x => x.CreatedAt)
        .Take(250).ToListAsync(ct));
});

app.MapGet("/api/work-orders/{id:guid}", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (order is null) return Results.NotFound();

    var lines = await db.WorkOrderLines.AsNoTracking().Where(x => x.WorkOrderId == id && x.TenantId == tenantId).ToListAsync(ct);
    var approvals = await db.CustomerApprovals.AsNoTracking().Where(x => x.WorkOrderId == id && x.TenantId == tenantId).ToListAsync(ct);
    var times = await db.TimeEntries.AsNoTracking().Where(x => x.WorkOrderId == id && x.TenantId == tenantId).ToListAsync(ct);
    return Results.Ok(new { order, lines, approvals, times });
});

app.MapPost("/api/work-orders/{id:guid}/intake", async (Guid id, IntakeRequest req, ErpDbContext db, WorkOrderWorkflowService workflow, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (order is null) return Results.NotFound();

    order.MileageIn = req.MileageIn;
    order.FuelOrChargeLevel = req.FuelOrChargeLevel?.Trim() ?? "";
    if (!string.IsNullOrWhiteSpace(req.CustomerRequest))
        order.CustomerRequest = req.CustomerRequest.Trim();

    try
    {
        if (order.Status == WorkOrderStatus.Scheduled)
            workflow.Transition(order, WorkOrderStatus.Arrived);
        if (order.Status == WorkOrderStatus.Arrived)
            workflow.Transition(order, WorkOrderStatus.Intake);
    }
    catch (InvalidOperationException ex)
    {
        return Results.BadRequest(new { error = ex.Message });
    }

    await db.SaveChangesAsync(ct);
    return Results.Ok(order);
});

app.MapPost("/api/work-orders/{id:guid}/transition", async (Guid id, TransitionRequest req, ErpDbContext db, WorkOrderWorkflowService workflow, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (order is null) return Results.NotFound();
    try { workflow.Transition(order, req.Status); }
    catch (InvalidOperationException ex) { return Results.BadRequest(new { error = ex.Message }); }
    await db.SaveChangesAsync(ct);
    return Results.Ok(order);
});

app.MapPost("/api/work-orders/{id:guid}/lines", async (Guid id, WorkOrderLineCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (!await db.WorkOrders.AnyAsync(x => x.Id == id && x.TenantId == tenantId, ct)) return Results.NotFound();
    var line = new WorkOrderLine
    {
        TenantId = tenantId, WorkOrderId = id, Type = req.Type,
        ItemNumber = req.ItemNumber?.Trim() ?? "", Description = req.Description.Trim(),
        Quantity = req.Quantity, UnitNet = req.UnitNet, VatRate = req.VatRate,
        DiscountPercent = req.DiscountPercent, InventoryItemId = req.InventoryItemId,
        EmployeeId = req.EmployeeId
    };
    db.WorkOrderLines.Add(line);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/work-orders/{id}/lines/{line.Id}", line);
});

app.MapPost("/api/work-orders/{id:guid}/approvals", async (Guid id, ApprovalCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (!await db.WorkOrders.AnyAsync(x => x.Id == id && x.TenantId == tenantId, ct)) return Results.NotFound();
    var approval = new CustomerApproval
    {
        TenantId = tenantId, WorkOrderId = id, OfferedGross = req.OfferedGross,
        Channel = req.Channel ?? "Link", Token = Convert.ToHexString(Guid.NewGuid().ToByteArray())
    };
    db.CustomerApprovals.Add(approval);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/work-orders/{id}/approvals/{approval.Id}", approval);
});

app.MapPost("/api/approvals/{id:guid}/respond", async (Guid id, ApprovalResponse req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var approval = await db.CustomerApprovals.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (approval is null) return Results.NotFound();
    approval.Status = req.Status;
    approval.ResponseNote = req.Note ?? "";
    approval.RespondedAt = DateTimeOffset.UtcNow;
    await db.SaveChangesAsync(ct);
    return Results.Ok(approval);
});

app.MapPost("/api/time/start", async (TimeStart req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var open = await db.TimeEntries.AnyAsync(x => x.TenantId == tenantId && x.EmployeeId == req.EmployeeId && x.EndedAt == null, ct);
    if (open) return Results.Conflict(new { error = "Mitarbeiter hat bereits eine laufende Zeiterfassung." });
    var entry = new TimeEntry { TenantId = tenantId, WorkOrderId = req.WorkOrderId, EmployeeId = req.EmployeeId, Activity = req.Activity ?? "", StartedAt = DateTimeOffset.UtcNow };
    db.TimeEntries.Add(entry);
    await db.SaveChangesAsync(ct);
    return Results.Ok(entry);
});

app.MapPost("/api/time/{id:guid}/stop", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var entry = await db.TimeEntries.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (entry is null) return Results.NotFound();
    entry.EndedAt ??= DateTimeOffset.UtcNow;
    await db.SaveChangesAsync(ct);
    return Results.Ok(entry);
});

app.MapGet("/api/inventory", async (string? q, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var query = db.InventoryItems.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (!string.IsNullOrWhiteSpace(q))
    {
        var s = q.Trim().ToLower();
        query = query.Where(x => x.ItemNumber.ToLower().Contains(s) || x.Description.ToLower().Contains(s) || x.Ean.ToLower().Contains(s));
    }
    return Results.Ok(await query.OrderBy(x => x.ItemNumber).Take(500).ToListAsync(ct));
});

app.MapPost("/api/inventory/{itemId:guid}/movement", async (Guid itemId, StockMovementCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var item = await db.InventoryItems.FirstOrDefaultAsync(x => x.Id == itemId && x.TenantId == tenantId, ct);
    if (item is null) return Results.NotFound();

    var delta = req.Type switch
    {
        StockMovementType.Receipt or StockMovementType.Return or StockMovementType.Adjustment => req.Quantity,
        StockMovementType.Consumption => -Math.Abs(req.Quantity),
        _ => 0m
    };
    if (item.Stock + delta < 0) return Results.BadRequest(new { error = "Bestand würde negativ." });

    item.Stock += delta;
    db.StockMovements.Add(new StockMovement
    {
        TenantId = tenantId, InventoryItemId = item.Id, SiteId = req.SiteId,
        Type = req.Type, Quantity = req.Quantity, Reference = req.Reference ?? ""
    });
    await db.SaveChangesAsync(ct);
    return Results.Ok(item);
});

app.MapGet("/api/tires", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.TireSets.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.StorageNumber).ToListAsync(ct));
});

app.MapPost("/api/tires", async (TireSetCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var tire = new TireSet
    {
        TenantId = tenantId, CustomerId = req.CustomerId, VehicleId = req.VehicleId,
        StorageNumber = req.StorageNumber.Trim(), Season = req.Season, BrandModel = req.BrandModel.Trim(),
        Size = req.Size.Trim(), Dot = req.Dot ?? "", FrontLeftMm = req.FrontLeftMm,
        FrontRightMm = req.FrontRightMm, RearLeftMm = req.RearLeftMm, RearRightMm = req.RearRightMm,
        Condition = req.Condition, StorageLocation = req.StorageLocation.Trim(), HasTpms = req.HasTpms
    };
    db.TireSets.Add(tire);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/tires/{tire.Id}", tire);
});

app.MapGet("/api/employees", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.Employees.AsNoTracking().Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).OrderBy(x => x.Name).ToListAsync(ct));
});

app.MapPost("/api/absences", async (AbsenceCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (req.To < req.From) return Results.BadRequest(new { error = "Bis-Datum liegt vor Von-Datum." });
    var absence = new Absence { TenantId = tenantId, EmployeeId = req.EmployeeId, Type = req.Type, From = req.From, To = req.To, Reason = req.Reason ?? "", Approved = req.Approved, AffectsCapacity = req.AffectsCapacity };
    db.Absences.Add(absence);
    await db.SaveChangesAsync(ct);
    return Results.Ok(absence);
});

app.MapPost("/api/invoices/from-work-order/{workOrderId:guid}", async (Guid workOrderId, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == workOrderId && x.TenantId == tenantId, ct);
    if (order is null) return Results.NotFound();
    var existing = await db.Invoices.FirstOrDefaultAsync(x => x.WorkOrderId == workOrderId && x.TenantId == tenantId && x.Status != InvoiceStatus.Cancelled, ct);
    if (existing is not null) return Results.Conflict(new { error = "Für diesen Auftrag existiert bereits eine Rechnung.", invoiceId = existing.Id });

    var orderLines = await db.WorkOrderLines.AsNoTracking().Where(x => x.WorkOrderId == workOrderId && x.TenantId == tenantId).ToListAsync(ct);
    var net = orderLines.Sum(x => x.NetTotal);
    var vat = orderLines.Sum(x => Math.Round(x.NetTotal * x.VatRate / 100m, 2));
    var invoiceNumber = await numbers.NextAsync(tenantId, order.SiteId, "invoice", "RE-", 5, true, ct);
    var invoice = new Invoice
    {
        TenantId = tenantId, SiteId = order.SiteId, CustomerId = order.CustomerId, VehicleId = order.VehicleId,
        WorkOrderId = order.Id, Number = invoiceNumber,
        IssueDate = DateOnly.FromDateTime(DateTime.UtcNow), DueDate = DateOnly.FromDateTime(DateTime.UtcNow.AddDays(14)),
        NetTotal = net, VatTotal = vat, GrossTotal = net + vat, Status = InvoiceStatus.Issued
    };
    db.Invoices.Add(invoice);
    foreach (var l in orderLines)
        db.InvoiceLines.Add(new InvoiceLine
        {
            TenantId = tenantId, InvoiceId = invoice.Id, Type = l.Type, Description = l.Description,
            Quantity = l.Quantity, UnitNet = l.UnitNet, VatRate = l.VatRate, DiscountPercent = l.DiscountPercent
        });
    order.Status = WorkOrderStatus.Invoiced;
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/invoices/{invoice.Id}", invoice);
});

app.MapGet("/api/invoices", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.Invoices.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.IssueDate).Take(250).ToListAsync(ct));
});

app.MapPost("/api/invoices/{id:guid}/payments", async (Guid id, PaymentCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var invoice = await db.Invoices.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (invoice is null) return Results.NotFound();
    if (req.Amount <= 0) return Results.BadRequest(new { error = "Zahlbetrag muss positiv sein." });

    var payment = new Payment { TenantId = tenantId, InvoiceId = id, Amount = req.Amount, Method = req.Method, Reference = req.Reference ?? "" };
    db.Payments.Add(payment);
    invoice.PaidTotal += req.Amount;
    invoice.Status = invoice.PaidTotal >= invoice.GrossTotal ? InvoiceStatus.Paid : InvoiceStatus.PartiallyPaid;
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { invoice, payment });
});


app.MapGet("/api/sites", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.Sites.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted)
        .OrderBy(x => x.Name).ToListAsync(ct));
});

app.MapGet("/api/resources", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.WorkshopResources.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted)
        .OrderBy(x => x.Name).ToListAsync(ct));
});

app.MapGet("/api/suppliers", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.Suppliers.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .OrderBy(x => x.Name).ToListAsync(ct));
});

app.MapPost("/api/purchase-orders", async (PurchaseOrderCreate req, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (!await db.Suppliers.AnyAsync(x => x.Id == req.SupplierId && x.TenantId == tenantId, ct))
        return Results.BadRequest(new { error = "Lieferant nicht gefunden." });

    var number = await numbers.NextAsync(tenantId, req.SiteId, "purchase-order", "BE-", 5, true, ct);
    var po = new PurchaseOrder
    {
        TenantId = tenantId, SupplierId = req.SupplierId, SiteId = req.SiteId,
        Number = number, Status = PurchaseOrderStatus.Ordered, OrderedAt = DateTimeOffset.UtcNow,
        ExpectedAt = req.ExpectedAt
    };
    db.PurchaseOrders.Add(po);

    foreach (var line in req.Lines)
    {
        db.PurchaseOrderLines.Add(new PurchaseOrderLine
        {
            TenantId = tenantId, PurchaseOrderId = po.Id, InventoryItemId = line.InventoryItemId,
            Quantity = line.Quantity, UnitPurchaseNet = line.UnitPurchaseNet
        });
    }

    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/purchase-orders/{po.Id}", po);
});

app.MapPost("/api/purchase-orders/{id:guid}/receive", async (Guid id, GoodsReceiptRequest req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    await using var tx = await db.Database.BeginTransactionAsync(ct);

    var po = await db.PurchaseOrders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId, ct);
    if (po is null) return Results.NotFound();

    foreach (var received in req.Lines)
    {
        var line = await db.PurchaseOrderLines.FirstOrDefaultAsync(x => x.Id == received.PurchaseOrderLineId && x.PurchaseOrderId == id && x.TenantId == tenantId, ct);
        if (line is null) return Results.BadRequest(new { error = $"Bestellposition {received.PurchaseOrderLineId} nicht gefunden." });
        if (received.Quantity <= 0 || line.ReceivedQuantity + received.Quantity > line.Quantity)
            return Results.BadRequest(new { error = "Ungültige Wareneingangsmenge." });

        var item = await db.InventoryItems.FirstAsync(x => x.Id == line.InventoryItemId && x.TenantId == tenantId, ct);
        line.ReceivedQuantity += received.Quantity;
        item.Stock += received.Quantity;
        db.StockMovements.Add(new StockMovement
        {
            TenantId = tenantId, InventoryItemId = item.Id, SiteId = po.SiteId,
            Type = StockMovementType.Receipt, Quantity = received.Quantity,
            Reference = $"Wareneingang {po.Number}"
        });
    }

    var allLines = await db.PurchaseOrderLines.Where(x => x.PurchaseOrderId == id && x.TenantId == tenantId).ToListAsync(ct);
    po.Status = allLines.All(x => x.ReceivedQuantity >= x.Quantity) ? PurchaseOrderStatus.Received : PurchaseOrderStatus.PartiallyReceived;
    await db.SaveChangesAsync(ct);
    await tx.CommitAsync(ct);
    return Results.Ok(po);
});

app.MapGet("/api/reminders", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.Reminders.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.Status == ReminderStatus.Open && !x.IsDeleted)
        .OrderBy(x => x.DueAt).Take(250).ToListAsync(ct));
});

app.MapGet("/api/loaners", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.LoanerVehicles.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted)
        .OrderBy(x => x.Number).ToListAsync(ct));
});


app.MapGet("/api/purchase-orders", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var orders = await db.PurchaseOrders.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .OrderByDescending(x => x.CreatedAt)
        .Take(250)
        .ToListAsync(ct);

    var ids = orders.Select(x => x.Id).ToList();
    var lines = await db.PurchaseOrderLines.AsNoTracking()
        .Where(x => x.TenantId == tenantId && ids.Contains(x.PurchaseOrderId) && !x.IsDeleted)
        .ToListAsync(ct);

    return Results.Ok(orders.Select(o => new
    {
        order = o,
        lines = lines.Where(x => x.PurchaseOrderId == o.Id).ToList()
    }));
});

app.MapGet("/api/absences", async (DateOnly? from, DateOnly? to, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var query = db.Absences.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (from is not null) query = query.Where(x => x.To >= from.Value);
    if (to is not null) query = query.Where(x => x.From <= to.Value);
    return Results.Ok(await query.OrderByDescending(x => x.From).Take(500).ToListAsync(ct));
});


app.MapGet("/api/admin/users", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var users = await db.UserProfiles.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .OrderBy(x => x.DisplayName)
        .ToListAsync(ct);
    var assignments = await db.UserRoleAssignments.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .ToListAsync(ct);

    return Results.Ok(users.Select(u => new
    {
        user = u,
        roleIds = assignments.Where(x => x.UserProfileId == u.Id).Select(x => x.RoleDefinitionId).Distinct().ToList()
    }));
});

app.MapGet("/api/admin/roles", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var roles = await db.RoleDefinitions.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .OrderBy(x => x.Name)
        .ToListAsync(ct);
    var rolePermissions = await db.RolePermissions.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .ToListAsync(ct);
    var permissions = await db.PermissionDefinitions.AsNoTracking()
        .Where(x => !x.IsDeleted)
        .ToListAsync(ct);

    return Results.Ok(roles.Select(r => new
    {
        role = r,
        permissions = rolePermissions.Where(x => x.RoleDefinitionId == r.Id && x.Effect == PermissionEffect.Allow)
            .Join(permissions, rp => rp.PermissionDefinitionId, p => p.Id, (_, p) => p.Key)
            .OrderBy(x => x)
            .ToList()
    }));
});

app.MapGet("/api/admin/permissions", async (ErpDbContext db, CancellationToken ct) =>
{
    return Results.Ok(await db.PermissionDefinitions.AsNoTracking()
        .Where(x => !x.IsDeleted)
        .OrderBy(x => x.Module).ThenBy(x => x.Key)
        .ToListAsync(ct));
});

app.MapPost("/api/admin/roles", async (RoleCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var name = req.Name.Trim();
    if (string.IsNullOrWhiteSpace(name)) return Results.BadRequest(new { error = "Rollenname fehlt." });
    if (await db.RoleDefinitions.AnyAsync(x => x.TenantId == tenantId && x.Name == name && !x.IsDeleted, ct))
        return Results.Conflict(new { error = "Rolle existiert bereits." });

    var role = new RoleDefinition
    {
        TenantId = tenantId, Name = name, Description = req.Description?.Trim() ?? "", SystemRole = false
    };
    db.RoleDefinitions.Add(role);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/admin/roles/{role.Id}", role);
});

app.MapPut("/api/admin/roles/{id:guid}/permissions", async (Guid id, RolePermissionsUpdate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var role = await db.RoleDefinitions.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (role is null) return Results.NotFound();

    var defs = await db.PermissionDefinitions.Where(x => req.PermissionKeys.Contains(x.Key) && !x.IsDeleted).ToListAsync(ct);
    var existing = await db.RolePermissions.Where(x => x.TenantId == tenantId && x.RoleDefinitionId == id).ToListAsync(ct);
    db.RolePermissions.RemoveRange(existing);
    foreach (var p in defs)
        db.RolePermissions.Add(new RolePermission { TenantId = tenantId, RoleDefinitionId = id, PermissionDefinitionId = p.Id, Effect = PermissionEffect.Allow });

    await db.SaveChangesAsync(ct);
    return Results.Ok(new { roleId = id, permissions = defs.Select(x => x.Key).OrderBy(x => x).ToList() });
});

app.MapPut("/api/admin/users/{profileId:guid}/roles", async (Guid profileId, UserRolesUpdate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (!await db.UserProfiles.AnyAsync(x => x.Id == profileId && x.TenantId == tenantId && !x.IsDeleted, ct))
        return Results.NotFound();

    var validRoles = await db.RoleDefinitions
        .Where(x => x.TenantId == tenantId && req.RoleIds.Contains(x.Id) && !x.IsDeleted)
        .Select(x => x.Id).ToListAsync(ct);

    var existing = await db.UserRoleAssignments
        .Where(x => x.TenantId == tenantId && x.UserProfileId == profileId)
        .ToListAsync(ct);
    db.UserRoleAssignments.RemoveRange(existing);
    foreach (var roleId in validRoles)
        db.UserRoleAssignments.Add(new UserRoleAssignment { TenantId = tenantId, UserProfileId = profileId, RoleDefinitionId = roleId, SiteId = req.SiteId });

    await db.SaveChangesAsync(ct);
    return Results.Ok(new { userProfileId = profileId, roleIds = validRoles });
});

app.MapPost("/api/employees", async (EmployeeCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var siteId = req.SiteId ?? await db.Sites.Where(x => x.TenantId == tenantId && x.Active).Select(x => x.Id).FirstAsync(ct);
    if (await db.Employees.AnyAsync(x => x.TenantId == tenantId && x.PersonnelNumber == req.PersonnelNumber && !x.IsDeleted, ct))
        return Results.Conflict(new { error = "Personalnummer existiert bereits." });

    var e = new Employee
    {
        TenantId = tenantId, SiteId = siteId, PersonnelNumber = req.PersonnelNumber.Trim(),
        Name = req.Name.Trim(), RoleName = req.RoleName?.Trim() ?? "", WeeklyHours = req.WeeklyHours,
        ProductiveHourlyRate = req.ProductiveHourlyRate, ProductiveHourlyCost = req.ProductiveHourlyCost,
        AnnualVacationDays = req.AnnualVacationDays, Active = true
    };
    db.Employees.Add(e);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/employees/{e.Id}", e);
});

app.MapPost("/api/resources", async (ResourceCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var siteId = req.SiteId ?? await db.Sites.Where(x => x.TenantId == tenantId && x.Active).Select(x => x.Id).FirstAsync(ct);
    var r = new WorkshopResource
    {
        TenantId = tenantId, SiteId = siteId, Name = req.Name.Trim(), Kind = req.Kind,
        MaxLoadKg = req.MaxLoadKg, MaxVehicleHeightM = req.MaxVehicleHeightM, SupportsEv = req.SupportsEv, Active = true
    };
    db.WorkshopResources.Add(r);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/resources/{r.Id}", r);
});

app.MapPost("/api/reminders", async (ReminderCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var reminder = new Reminder
    {
        TenantId = tenantId, CustomerId = req.CustomerId, VehicleId = req.VehicleId,
        Type = req.Type.Trim(), Subject = req.Subject.Trim(), DueAt = req.DueAt,
        Status = ReminderStatus.Open, PreferredChannel = req.PreferredChannel
    };
    db.Reminders.Add(reminder);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/reminders/{reminder.Id}", reminder);
});

app.MapPut("/api/reminders/{id:guid}/status", async (Guid id, ReminderStatusUpdate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var reminder = await db.Reminders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (reminder is null) return Results.NotFound();
    reminder.Status = req.Status;
    await db.SaveChangesAsync(ct);
    return Results.Ok(reminder);
});

app.MapGet("/api/reports/overview", async (int? year, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var targetYear = year ?? DateTime.UtcNow.Year - 1;
    var from = new DateOnly(targetYear, 1, 1);
    var to = new DateOnly(targetYear, 12, 31);

    var invoices = await db.Invoices.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.IssueDate >= from && x.IssueDate <= to &&
                    x.Status != InvoiceStatus.Cancelled && x.Status != InvoiceStatus.Credited && !x.IsDeleted)
        .ToListAsync(ct);

    var customerCount = await db.Customers.CountAsync(x => x.TenantId == tenantId && !x.IsDeleted, ct);
    var vehicleCount = await db.Vehicles.CountAsync(x => x.TenantId == tenantId && !x.IsDeleted, ct);
    var netRevenue = invoices.Sum(x => x.NetTotal);
    var grossRevenue = invoices.Sum(x => x.GrossTotal);
    var paid = invoices.Sum(x => x.PaidTotal);
    var invoiceCount = invoices.Count;
    var averageInvoiceNet = invoiceCount == 0 ? 0m : Math.Round(netRevenue / invoiceCount, 2);

    var monthly = Enumerable.Range(1, 12).Select(month => new
    {
        month,
        net = invoices.Where(x => x.IssueDate.Month == month).Sum(x => x.NetTotal),
        gross = invoices.Where(x => x.IssueDate.Month == month).Sum(x => x.GrossTotal),
        count = invoices.Count(x => x.IssueDate.Month == month)
    }).ToList();

    var topCustomerIds = invoices
        .GroupBy(x => x.CustomerId)
        .Select(g => new { customerId = g.Key, net = g.Sum(x => x.NetTotal), count = g.Count() })
        .OrderByDescending(x => x.net)
        .Take(8)
        .ToList();

    var customerIds = topCustomerIds.Select(x => x.customerId).ToList();
    var customerNames = await db.Customers.AsNoTracking()
        .Where(x => x.TenantId == tenantId && customerIds.Contains(x.Id))
        .ToDictionaryAsync(x => x.Id, x => x.DisplayName, ct);

    var topCustomers = topCustomerIds.Select(x => new
    {
        x.customerId,
        name = customerNames.GetValueOrDefault(x.customerId, "Unbekannt"),
        x.net,
        x.count
    }).ToList();

    return Results.Ok(new
    {
        year = targetYear,
        netRevenue,
        grossRevenue,
        paid,
        invoiceCount,
        averageInvoiceNet,
        customerCount,
        vehicleCount,
        monthly,
        topCustomers
    });
});

app.MapGet("/api/admin/security-summary", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(new
    {
        users = await db.UserProfiles.CountAsync(x => x.TenantId == tenantId && x.Active && !x.IsDeleted, ct),
        roles = await db.RoleDefinitions.CountAsync(x => x.TenantId == tenantId && !x.IsDeleted, ct),
        permissions = await db.PermissionDefinitions.CountAsync(x => !x.IsDeleted, ct),
        sites = await db.Sites.CountAsync(x => x.TenantId == tenantId && x.Active && !x.IsDeleted, ct),
        auditEntries = await db.AuditEntries.CountAsync(x => x.TenantId == tenantId && !x.IsDeleted, ct)
    });
});

app.MapGet("/api/dashboard", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var today = DateTimeOffset.UtcNow.Date;
    var tomorrow = today.AddDays(1);
    var appointments = await db.Appointments.CountAsync(x => x.TenantId == tenantId && x.StartsAt >= today && x.StartsAt < tomorrow, ct);
    var openOrders = await db.WorkOrders.CountAsync(x => x.TenantId == tenantId && x.Status != WorkOrderStatus.Closed && x.Status != WorkOrderStatus.Cancelled, ct);
    var lowStock = await db.InventoryItems.CountAsync(x => x.TenantId == tenantId && x.Stock <= x.MinimumStock, ct);
    var receivables = await db.Invoices.Where(x => x.TenantId == tenantId && x.Status != InvoiceStatus.Paid && x.Status != InvoiceStatus.Cancelled).SumAsync(x => (decimal?)(x.GrossTotal - x.PaidTotal), ct) ?? 0m;
    return Results.Ok(new { appointments, openOrders, lowStock, receivables });
});

app.Run();

record LoginRequest(string Username, string Password);
record CustomerCreate(string DisplayName, string? CompanyName, string? FirstName, string? LastName, string? Email, string? Phone, string? Mobile, string? Street, string? PostalCode, string? City, string? Notes);
record VehicleCreate(Guid CustomerId, string LicensePlate, string? Vin, string? Make, string? Model, string? Type, string? Hsn, string? Tsn, DateOnly? FirstRegistration, int? Mileage, DateOnly? NextHu, DateOnly? NextService);
record AppointmentCreate(Guid? SiteId, Guid CustomerId, Guid VehicleId, Guid? ResourceId, Guid? EmployeeId, DateTimeOffset StartsAt, DateTimeOffset EndsAt, string Subject, string? CustomerRequest);
record IntakeRequest(int? MileageIn, string? FuelOrChargeLevel, string? CustomerRequest);
record TransitionRequest(WorkOrderStatus Status);
record WorkOrderLineCreate(LineType Type, string? ItemNumber, string Description, decimal Quantity, decimal UnitNet, decimal VatRate, decimal DiscountPercent, Guid? InventoryItemId, Guid? EmployeeId);
record ApprovalCreate(decimal OfferedGross, string? Channel);
record ApprovalResponse(ApprovalStatus Status, string? Note);
record TimeStart(Guid WorkOrderId, Guid EmployeeId, string? Activity);
record StockMovementCreate(Guid SiteId, StockMovementType Type, decimal Quantity, string? Reference);
record TireSetCreate(Guid CustomerId, Guid VehicleId, string StorageNumber, TireSeason Season, string BrandModel, string Size, string? Dot, decimal FrontLeftMm, decimal FrontRightMm, decimal RearLeftMm, decimal RearRightMm, TireCondition Condition, string StorageLocation, bool HasTpms);
record AbsenceCreate(Guid EmployeeId, AbsenceType Type, DateOnly From, DateOnly To, string? Reason, bool Approved, bool AffectsCapacity);
record PaymentCreate(decimal Amount, PaymentMethod Method, string? Reference);
record PurchaseOrderLineCreate(Guid InventoryItemId, decimal Quantity, decimal UnitPurchaseNet);
record PurchaseOrderCreate(Guid SupplierId, Guid SiteId, DateTimeOffset? ExpectedAt, List<PurchaseOrderLineCreate> Lines);
record GoodsReceiptLine(Guid PurchaseOrderLineId, decimal Quantity);
record GoodsReceiptRequest(List<GoodsReceiptLine> Lines);
record RoleCreate(string Name, string? Description);
record RolePermissionsUpdate(List<string> PermissionKeys);
record UserRolesUpdate(List<Guid> RoleIds, Guid? SiteId);
record EmployeeCreate(Guid? SiteId, string PersonnelNumber, string Name, string? RoleName, decimal WeeklyHours, decimal ProductiveHourlyCost, decimal ProductiveHourlyRate, int AnnualVacationDays);
record ResourceCreate(Guid? SiteId, string Name, ResourceKind Kind, decimal? MaxLoadKg, decimal? MaxVehicleHeightM, bool SupportsEv);
record ReminderCreate(Guid CustomerId, Guid? VehicleId, string Type, string Subject, DateTimeOffset DueAt, CommunicationChannel PreferredChannel);
record ReminderStatusUpdate(ReminderStatus Status);
