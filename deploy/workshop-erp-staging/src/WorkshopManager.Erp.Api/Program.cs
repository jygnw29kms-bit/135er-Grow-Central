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
    if (p.StartsWith("/api/employees") || p.StartsWith("/api/absences") || p.StartsWith("/api/personnel")) return write ? "personnel.write" : "personnel.read";
    if (p.StartsWith("/api/invoices") || p.StartsWith("/api/finance") || p.StartsWith("/api/quotes")) return write ? "billing.write" : "billing.read";
    if (p.StartsWith("/api/resources")) return write ? "resources.write" : "resources.read";
    if (p.StartsWith("/api/reminders") || p.StartsWith("/api/communications")) return write ? "crm.write" : "crm.read";
    if (p.StartsWith("/api/checklists")) return write ? "orders.write" : "orders.read";
    if (p.StartsWith("/api/loaner-bookings") || p.StartsWith("/api/loaners")) return write ? "loaners.write" : "loaners.read";
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

app.MapPut("/api/customers/{id:guid}", async (Guid id, CustomerCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var x = await db.Customers.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (x is null) return Results.NotFound();
    x.DisplayName = req.DisplayName.Trim();
    x.CompanyName = req.CompanyName?.Trim() ?? "";
    x.FirstName = req.FirstName?.Trim() ?? "";
    x.LastName = req.LastName?.Trim() ?? "";
    x.Email = req.Email?.Trim() ?? "";
    x.Phone = req.Phone?.Trim() ?? "";
    x.Mobile = req.Mobile?.Trim() ?? "";
    x.Street = req.Street?.Trim() ?? "";
    x.PostalCode = req.PostalCode?.Trim() ?? "";
    x.City = req.City?.Trim() ?? "";
    x.Notes = req.Notes?.Trim() ?? "";
    await db.SaveChangesAsync(ct);
    return Results.Ok(x);
});

app.MapPut("/api/vehicles/{id:guid}", async (Guid id, VehicleCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var x = await db.Vehicles.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (x is null) return Results.NotFound();
    if (!await db.Customers.AnyAsync(y => y.Id == req.CustomerId && y.TenantId == tenantId && !y.IsDeleted, ct))
        return Results.BadRequest(new { error = "Kunde nicht gefunden." });

    x.CustomerId = req.CustomerId;
    x.LicensePlate = req.LicensePlate.Trim().ToUpperInvariant();
    x.Vin = req.Vin?.Trim().ToUpperInvariant() ?? "";
    x.Make = req.Make?.Trim() ?? "";
    x.Model = req.Model?.Trim() ?? "";
    x.Type = req.Type?.Trim() ?? "";
    x.Hsn = req.Hsn?.Trim() ?? "";
    x.Tsn = req.Tsn?.Trim() ?? "";
    x.FirstRegistration = req.FirstRegistration;
    x.Mileage = req.Mileage;
    x.NextHu = req.NextHu;
    x.NextService = req.NextService;
    await db.SaveChangesAsync(ct);
    return Results.Ok(x);
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

app.MapPut("/api/appointments/{id:guid}", async (Guid id, AppointmentCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var a = await db.Appointments.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (a is null) return Results.NotFound();
    a.SiteId = req.SiteId ?? a.SiteId;
    a.CustomerId = req.CustomerId;
    a.VehicleId = req.VehicleId;
    a.ResourceId = req.ResourceId;
    a.EmployeeId = req.EmployeeId;
    a.StartsAt = req.StartsAt;
    a.EndsAt = req.EndsAt;
    a.Subject = req.Subject.Trim();
    a.CustomerRequest = req.CustomerRequest?.Trim() ?? "";
    await db.SaveChangesAsync(ct);
    return Results.Ok(a);
});

app.MapPost("/api/appointments/{id:guid}/cancel", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var a = await db.Appointments.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (a is null) return Results.NotFound();
    a.Status = AppointmentStatus.Cancelled;
    await db.SaveChangesAsync(ct);
    return Results.Ok(a);
});

app.MapPost("/api/work-orders", async (WorkOrderCreate req, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var siteId = req.SiteId ?? await db.Sites.Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).Select(x => x.Id).FirstAsync(ct);
    if (!await db.Customers.AnyAsync(x => x.Id == req.CustomerId && x.TenantId == tenantId && !x.IsDeleted, ct))
        return Results.BadRequest(new { error = "Kunde nicht gefunden." });
    if (!await db.Vehicles.AnyAsync(x => x.Id == req.VehicleId && x.CustomerId == req.CustomerId && x.TenantId == tenantId && !x.IsDeleted, ct))
        return Results.BadRequest(new { error = "Fahrzeug passt nicht zum Kunden." });

    var number = await numbers.NextAsync(tenantId, siteId, "work-order", "AU-", 5, true, ct);
    var order = new WorkOrder
    {
        TenantId = tenantId,
        SiteId = siteId,
        CustomerId = req.CustomerId,
        VehicleId = req.VehicleId,
        Number = number,
        Status = WorkOrderStatus.Draft,
        CustomerRequest = req.CustomerRequest?.Trim() ?? "",
        Diagnosis = req.Diagnosis?.Trim() ?? "",
        PromisedAt = req.PromisedAt
    };
    db.WorkOrders.Add(order);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/work-orders/{order.Id}", order);
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

app.MapPost("/api/work-orders/{id:guid}/inventory-line", async (Guid id, InventoryLineCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (order is null) return Results.NotFound();
    var item = await db.InventoryItems.FirstOrDefaultAsync(x => x.Id == req.InventoryItemId && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (item is null) return Results.BadRequest(new { error = "Artikel nicht gefunden." });
    if (req.Quantity <= 0) return Results.BadRequest(new { error = "Menge muss positiv sein." });
    if (item.Stock < req.Quantity) return Results.BadRequest(new { error = $"Nicht genügend Bestand. Verfügbar: {item.Stock}" });

    await using var tx = await db.Database.BeginTransactionAsync(ct);
    var line = new WorkOrderLine
    {
        TenantId = tenantId,
        WorkOrderId = order.Id,
        Type = LineType.Part,
        ItemNumber = item.ItemNumber,
        Description = item.Description,
        Quantity = req.Quantity,
        UnitNet = req.UnitNet ?? item.SaleNet,
        VatRate = req.VatRate ?? 19m,
        DiscountPercent = req.DiscountPercent ?? 0m,
        InventoryItemId = item.Id,
        ApprovedByCustomer = req.ApprovedByCustomer
    };
    db.WorkOrderLines.Add(line);

    var isQuote = order.Number.StartsWith("KV-", StringComparison.OrdinalIgnoreCase);
    if (!isQuote)
    {
        item.Stock -= req.Quantity;
        db.StockMovements.Add(new StockMovement
        {
            TenantId = tenantId,
            InventoryItemId = item.Id,
            SiteId = order.SiteId,
            Type = StockMovementType.Consumption,
            Quantity = req.Quantity,
            Reference = $"Auftrag {order.Number}"
        });
    }

    await db.SaveChangesAsync(ct);
    await tx.CommitAsync(ct);
    return Results.Created($"/api/work-orders/{order.Id}/lines/{line.Id}", new { line, stock = item.Stock, reservedOnly = isQuote });
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

app.MapPost("/api/inventory", async (InventoryItemCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (await db.InventoryItems.AnyAsync(x => x.TenantId == tenantId && x.ItemNumber == req.ItemNumber && !x.IsDeleted, ct))
        return Results.Conflict(new { error = "Artikelnummer existiert bereits." });

    var item = new InventoryItem
    {
        TenantId = tenantId,
        ItemNumber = req.ItemNumber.Trim(),
        Ean = req.Ean?.Trim() ?? "",
        Manufacturer = req.Manufacturer?.Trim() ?? "",
        Description = req.Description.Trim(),
        PurchaseNet = req.PurchaseNet,
        SaleNet = req.SaleNet,
        Stock = req.Stock,
        MinimumStock = req.MinimumStock,
        StorageLocation = req.StorageLocation?.Trim() ?? "",
        PreferredSupplierId = req.PreferredSupplierId
    };
    db.InventoryItems.Add(item);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/inventory/{item.Id}", item);
});

app.MapPut("/api/inventory/{id:guid}", async (Guid id, InventoryItemCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var item = await db.InventoryItems.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (item is null) return Results.NotFound();

    item.ItemNumber = req.ItemNumber.Trim();
    item.Ean = req.Ean?.Trim() ?? "";
    item.Manufacturer = req.Manufacturer?.Trim() ?? "";
    item.Description = req.Description.Trim();
    item.PurchaseNet = req.PurchaseNet;
    item.SaleNet = req.SaleNet;
    item.MinimumStock = req.MinimumStock;
    item.StorageLocation = req.StorageLocation?.Trim() ?? "";
    item.PreferredSupplierId = req.PreferredSupplierId;
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

app.MapPut("/api/tires/{id:guid}", async (Guid id, TireSetCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var tire = await db.TireSets.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (tire is null) return Results.NotFound();

    tire.CustomerId = req.CustomerId;
    tire.VehicleId = req.VehicleId;
    tire.StorageNumber = req.StorageNumber.Trim();
    tire.Season = req.Season;
    tire.BrandModel = req.BrandModel.Trim();
    tire.Size = req.Size.Trim();
    tire.Dot = req.Dot ?? "";
    tire.FrontLeftMm = req.FrontLeftMm;
    tire.FrontRightMm = req.FrontRightMm;
    tire.RearLeftMm = req.RearLeftMm;
    tire.RearRightMm = req.RearRightMm;
    tire.Condition = req.Condition;
    tire.StorageLocation = req.StorageLocation.Trim();
    tire.HasTpms = req.HasTpms;
    await db.SaveChangesAsync(ct);
    return Results.Ok(tire);
});

app.MapPost("/api/tires/{id:guid}/checkout", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var tire = await db.TireSets.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (tire is null) return Results.NotFound();

    tire.IsDeleted = true;
    db.AuditEntries.Add(new AuditEntry
    {
        TenantId = tenantId,
        Actor = "staging-user",
        Action = "tire-checkout",
        EntityType = "TireSet",
        EntityId = tire.Id,
        NewJson = $"{{\"storageNumber\":\"{tire.StorageNumber}\"}}"
    });
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { id = tire.Id, checkedOut = true });
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

app.MapGet("/api/invoices/{id:guid}", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var invoice = await db.Invoices.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (invoice is null) return Results.NotFound();
    var lines = await db.InvoiceLines.AsNoTracking().Where(x => x.InvoiceId == id && x.TenantId == tenantId && !x.IsDeleted).ToListAsync(ct);
    var payments = await db.Payments.AsNoTracking().Where(x => x.InvoiceId == id && x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.PaidAt).ToListAsync(ct);
    return Results.Ok(new { invoice, lines, payments });
});

app.MapPost("/api/invoices/{id:guid}/reverse", async (Guid id, InvoiceReverseRequest req, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var original = await db.Invoices.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (original is null) return Results.NotFound();
    if (original.Status is InvoiceStatus.Cancelled or InvoiceStatus.Credited)
        return Results.Conflict(new { error = "Rechnung wurde bereits storniert oder gutgeschrieben." });

    var originalLines = await db.InvoiceLines.AsNoTracking().Where(x => x.InvoiceId == id && x.TenantId == tenantId && !x.IsDeleted).ToListAsync(ct);
    var isCredit = req.Kind.Equals("credit", StringComparison.OrdinalIgnoreCase);
    var prefix = isCredit ? "GS-" : "ST-";
    var key = isCredit ? "credit-note" : "cancellation";
    var number = await numbers.NextAsync(tenantId, original.SiteId, key, prefix, 5, true, ct);

    var reversal = new Invoice
    {
        TenantId = tenantId,
        SiteId = original.SiteId,
        CustomerId = original.CustomerId,
        VehicleId = original.VehicleId,
        WorkOrderId = original.WorkOrderId,
        Number = number,
        IssueDate = DateOnly.FromDateTime(DateTime.UtcNow),
        DueDate = DateOnly.FromDateTime(DateTime.UtcNow),
        NetTotal = -original.NetTotal,
        VatTotal = -original.VatTotal,
        GrossTotal = -original.GrossTotal,
        PaidTotal = original.PaidTotal > 0 ? -original.PaidTotal : 0m,
        Status = original.PaidTotal > 0 ? InvoiceStatus.Paid : InvoiceStatus.Issued
    };
    db.Invoices.Add(reversal);

    foreach (var l in originalLines)
    {
        db.InvoiceLines.Add(new InvoiceLine
        {
            TenantId = tenantId,
            InvoiceId = reversal.Id,
            Type = l.Type,
            Description = $"{(isCredit ? "Gutschrift" : "Storno")} zu {original.Number}: {l.Description}",
            Quantity = -l.Quantity,
            UnitNet = l.UnitNet,
            VatRate = l.VatRate,
            DiscountPercent = l.DiscountPercent
        });
    }

    original.Status = isCredit ? InvoiceStatus.Credited : InvoiceStatus.Cancelled;
    db.AuditEntries.Add(new AuditEntry
    {
        TenantId = tenantId,
        Actor = "staging-user",
        Action = isCredit ? "invoice-credit" : "invoice-cancel",
        EntityType = "Invoice",
        EntityId = original.Id,
        NewJson = System.Text.Json.JsonSerializer.Serialize(new { source = original.Number, followUp = number, reason = req.Reason ?? "" })
    });

    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/invoices/{reversal.Id}", new { source = original, reversal });
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

app.MapPost("/api/suppliers", async (SupplierCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var next = await db.Suppliers.CountAsync(x => x.TenantId == tenantId, ct) + 1;
    var supplier = new Supplier
    {
        TenantId = tenantId,
        SupplierNumber = string.IsNullOrWhiteSpace(req.SupplierNumber) ? $"L-{next:000}" : req.SupplierNumber.Trim(),
        Name = req.Name.Trim(),
        Email = req.Email?.Trim() ?? "",
        Phone = req.Phone?.Trim() ?? ""
    };
    db.Suppliers.Add(supplier);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/suppliers/{supplier.Id}", supplier);
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


app.MapGet("/api/loaner-bookings", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.LoanerBookings.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted)
        .OrderByDescending(x => x.From).Take(250).ToListAsync(ct));
});

app.MapPost("/api/loaners", async (LoanerCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var siteId = req.SiteId ?? await db.Sites.Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).Select(x => x.Id).FirstAsync(ct);
    var l = new LoanerVehicle
    {
        TenantId = tenantId, SiteId = siteId, Number = req.Number.Trim(),
        LicensePlate = req.LicensePlate.Trim().ToUpperInvariant(), VehicleName = req.VehicleName.Trim(),
        Mileage = req.Mileage, FuelOrChargeLevel = req.FuelOrChargeLevel?.Trim() ?? "", Active = true
    };
    db.LoanerVehicles.Add(l);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/loaners/{l.Id}", l);
});

app.MapPost("/api/loaner-bookings", async (LoanerBookingCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (req.To <= req.From) return Results.BadRequest(new { error = "Rückgabe muss nach Ausgabe liegen." });
    var conflict = await db.LoanerBookings.AnyAsync(x => x.TenantId == tenantId && x.LoanerVehicleId == req.LoanerVehicleId &&
        x.Status != LoanerBookingStatus.Cancelled && x.Status != LoanerBookingStatus.Returned && x.From < req.To && x.To > req.From, ct);
    if (conflict) return Results.Conflict(new { error = "Leihwagen ist im Zeitraum bereits reserviert." });

    var b = new LoanerBooking
    {
        TenantId = tenantId, LoanerVehicleId = req.LoanerVehicleId, CustomerId = req.CustomerId,
        WorkOrderId = req.WorkOrderId, From = req.From, To = req.To, Status = LoanerBookingStatus.Reserved
    };
    db.LoanerBookings.Add(b);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/loaner-bookings/{b.Id}", b);
});

app.MapPost("/api/loaner-bookings/{id:guid}/handover", async (Guid id, LoanerHandover req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var b = await db.LoanerBookings.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (b is null) return Results.NotFound();
    b.Status = LoanerBookingStatus.HandedOut;
    b.MileageOut = req.Mileage;
    b.FuelOut = req.FuelOrChargeLevel ?? "";
    b.DamageOut = req.Damage ?? "";
    await db.SaveChangesAsync(ct);
    return Results.Ok(b);
});

app.MapPost("/api/loaner-bookings/{id:guid}/return", async (Guid id, LoanerHandover req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var b = await db.LoanerBookings.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (b is null) return Results.NotFound();
    b.Status = LoanerBookingStatus.Returned;
    b.MileageIn = req.Mileage;
    b.FuelIn = req.FuelOrChargeLevel ?? "";
    b.DamageIn = req.Damage ?? "";
    var car = await db.LoanerVehicles.FirstOrDefaultAsync(x => x.Id == b.LoanerVehicleId && x.TenantId == tenantId, ct);
    if (car is not null && req.Mileage.HasValue) car.Mileage = req.Mileage.Value;
    await db.SaveChangesAsync(ct);
    return Results.Ok(b);
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

app.MapGet("/api/checklists/templates", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var templates = await db.ChecklistTemplates.AsNoTracking().Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).OrderBy(x => x.Name).ToListAsync(ct);
    var ids = templates.Select(x => x.Id).ToList();
    var fields = await db.ChecklistFields.AsNoTracking().Where(x => x.TenantId == tenantId && ids.Contains(x.ChecklistTemplateId) && !x.IsDeleted).OrderBy(x => x.SortOrder).ToListAsync(ct);
    return Results.Ok(templates.Select(t => new { template = t, fields = fields.Where(f => f.ChecklistTemplateId == t.Id).ToList() }));
});

app.MapPost("/api/checklists/run", async (ChecklistRunCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var run = new ChecklistRun
    {
        TenantId = tenantId, ChecklistTemplateId = req.ChecklistTemplateId, WorkOrderId = req.WorkOrderId,
        VehicleId = req.VehicleId, EmployeeId = req.EmployeeId, StartedAt = DateTimeOffset.UtcNow
    };
    db.ChecklistRuns.Add(run);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/checklists/run/{run.Id}", run);
});

app.MapPost("/api/checklists/run/{id:guid}/complete", async (Guid id, ChecklistComplete req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var run = await db.ChecklistRuns.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (run is null) return Results.NotFound();

    foreach (var a in req.Answers)
        db.ChecklistAnswers.Add(new ChecklistAnswer { TenantId = tenantId, ChecklistRunId = run.Id, ChecklistFieldId = a.FieldId, ValueJson = a.ValueJson ?? "null" });
    run.CompletedAt = DateTimeOffset.UtcNow;
    await db.SaveChangesAsync(ct);
    return Results.Ok(run);
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


app.MapGet("/api/customers/{id:guid}/history", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var customer = await db.Customers.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (customer is null) return Results.NotFound();

    var vehicles = await db.Vehicles.AsNoTracking().Where(x => x.CustomerId == id && x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.LicensePlate).ToListAsync(ct);
    var orders = await db.WorkOrders.AsNoTracking().Where(x => x.CustomerId == id && x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.CreatedAt).Take(100).ToListAsync(ct);
    var invoices = await db.Invoices.AsNoTracking().Where(x => x.CustomerId == id && x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.IssueDate).Take(100).ToListAsync(ct);
    var tires = await db.TireSets.AsNoTracking().Where(x => x.CustomerId == id && x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.StorageNumber).ToListAsync(ct);
    var reminders = await db.Reminders.AsNoTracking().Where(x => x.CustomerId == id && x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.DueAt).Take(100).ToListAsync(ct);

    return Results.Ok(new { customer, vehicles, orders, invoices, tires, reminders });
});

app.MapGet("/api/vehicles/{id:guid}/history", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var vehicle = await db.Vehicles.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (vehicle is null) return Results.NotFound();

    var orders = await db.WorkOrders.AsNoTracking().Where(x => x.VehicleId == id && x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.CreatedAt).Take(100).ToListAsync(ct);
    var invoices = await db.Invoices.AsNoTracking().Where(x => x.VehicleId == id && x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.IssueDate).Take(100).ToListAsync(ct);
    var tires = await db.TireSets.AsNoTracking().Where(x => x.VehicleId == id && x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.StorageNumber).ToListAsync(ct);
    var appointments = await db.Appointments.AsNoTracking().Where(x => x.VehicleId == id && x.TenantId == tenantId && !x.IsDeleted).OrderByDescending(x => x.StartsAt).Take(100).ToListAsync(ct);

    return Results.Ok(new { vehicle, orders, invoices, tires, appointments });
});

app.MapPut("/api/work-orders/{id:guid}", async (Guid id, WorkOrderUpdate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (order is null) return Results.NotFound();
    if (order.Status >= WorkOrderStatus.Invoiced)
        return Results.Conflict(new { error = "Fakturierte oder abgeschlossene Aufträge können nicht mehr direkt geändert werden." });

    order.CustomerRequest = req.CustomerRequest?.Trim() ?? "";
    order.Diagnosis = req.Diagnosis?.Trim() ?? "";
    order.PromisedAt = req.PromisedAt;
    order.MileageIn = req.MileageIn;
    order.FuelOrChargeLevel = req.FuelOrChargeLevel?.Trim() ?? "";
    await db.SaveChangesAsync(ct);
    return Results.Ok(order);
});

app.MapPut("/api/work-orders/{workOrderId:guid}/lines/{lineId:guid}", async (Guid workOrderId, Guid lineId, WorkOrderLineUpdate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == workOrderId && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (order is null) return Results.NotFound();
    if (order.Status >= WorkOrderStatus.Invoiced)
        return Results.Conflict(new { error = "Positionen eines fakturierten Auftrags können nicht geändert werden." });
    if (req.Quantity <= 0) return Results.BadRequest(new { error = "Menge muss größer als 0 sein." });

    var line = await db.WorkOrderLines.FirstOrDefaultAsync(x => x.Id == lineId && x.WorkOrderId == workOrderId && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (line is null) return Results.NotFound();

    await using var tx = await db.Database.BeginTransactionAsync(ct);
    if (line.InventoryItemId is Guid inventoryId)
    {
        var item = await db.InventoryItems.FirstOrDefaultAsync(x => x.Id == inventoryId && x.TenantId == tenantId && !x.IsDeleted, ct);
        if (item is null) return Results.Conflict(new { error = "Verknüpfter Lagerartikel fehlt." });

        var delta = req.Quantity - line.Quantity;
        if (delta > 0)
        {
            if (item.Stock < delta) return Results.BadRequest(new { error = $"Nicht genügend Bestand. Verfügbar: {item.Stock}" });
            item.Stock -= delta;
            db.StockMovements.Add(new StockMovement { TenantId = tenantId, InventoryItemId = item.Id, SiteId = order.SiteId, Type = StockMovementType.Consumption, Quantity = delta, Reference = $"Auftrag {order.Number} · Mengenänderung" });
        }
        else if (delta < 0)
        {
            item.Stock += -delta;
            db.StockMovements.Add(new StockMovement { TenantId = tenantId, InventoryItemId = item.Id, SiteId = order.SiteId, Type = StockMovementType.Return, Quantity = -delta, Reference = $"Auftrag {order.Number} · Rückbuchung" });
        }
    }

    line.Type = req.Type;
    line.ItemNumber = req.ItemNumber?.Trim() ?? line.ItemNumber;
    line.Description = req.Description.Trim();
    line.Quantity = req.Quantity;
    line.UnitNet = req.UnitNet;
    line.VatRate = req.VatRate;
    line.DiscountPercent = req.DiscountPercent;
    line.ApprovedByCustomer = req.ApprovedByCustomer;
    await db.SaveChangesAsync(ct);
    await tx.CommitAsync(ct);
    return Results.Ok(line);
});

app.MapDelete("/api/work-orders/{workOrderId:guid}/lines/{lineId:guid}", async (Guid workOrderId, Guid lineId, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == workOrderId && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (order is null) return Results.NotFound();
    if (order.Status >= WorkOrderStatus.Invoiced)
        return Results.Conflict(new { error = "Positionen eines fakturierten Auftrags können nicht gelöscht werden." });

    var line = await db.WorkOrderLines.FirstOrDefaultAsync(x => x.Id == lineId && x.WorkOrderId == workOrderId && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (line is null) return Results.NotFound();

    if (line.InventoryItemId is Guid inventoryId)
    {
        var item = await db.InventoryItems.FirstOrDefaultAsync(x => x.Id == inventoryId && x.TenantId == tenantId && !x.IsDeleted, ct);
        if (item is not null)
        {
            item.Stock += line.Quantity;
            db.StockMovements.Add(new StockMovement { TenantId = tenantId, InventoryItemId = item.Id, SiteId = order.SiteId, Type = StockMovementType.Return, Quantity = line.Quantity, Reference = $"Auftrag {order.Number} · Position gelöscht" });
        }
    }

    line.IsDeleted = true;
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { id = line.Id, deleted = true });
});

app.MapPut("/api/employees/{id:guid}", async (Guid id, EmployeeCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var e = await db.Employees.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (e is null) return Results.NotFound();
    e.SiteId = req.SiteId ?? e.SiteId;
    e.PersonnelNumber = req.PersonnelNumber.Trim();
    e.Name = req.Name.Trim();
    e.RoleName = req.RoleName?.Trim() ?? "";
    e.WeeklyHours = req.WeeklyHours;
    e.ProductiveHourlyCost = req.ProductiveHourlyCost;
    e.ProductiveHourlyRate = req.ProductiveHourlyRate;
    e.AnnualVacationDays = req.AnnualVacationDays;
    await db.SaveChangesAsync(ct);
    return Results.Ok(e);
});

app.MapPut("/api/absences/{id:guid}", async (Guid id, AbsenceCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (req.To < req.From) return Results.BadRequest(new { error = "Bis-Datum liegt vor Von-Datum." });
    var a = await db.Absences.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (a is null) return Results.NotFound();
    a.EmployeeId = req.EmployeeId;
    a.Type = req.Type;
    a.From = req.From;
    a.To = req.To;
    a.Reason = req.Reason?.Trim() ?? "";
    a.Approved = req.Approved;
    a.AffectsCapacity = req.AffectsCapacity;
    await db.SaveChangesAsync(ct);
    return Results.Ok(a);
});

app.MapDelete("/api/absences/{id:guid}", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var a = await db.Absences.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (a is null) return Results.NotFound();
    a.IsDeleted = true;
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { id = a.Id, deleted = true });
});

app.MapPut("/api/suppliers/{id:guid}", async (Guid id, SupplierCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var s = await db.Suppliers.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (s is null) return Results.NotFound();
    if (!string.IsNullOrWhiteSpace(req.SupplierNumber)) s.SupplierNumber = req.SupplierNumber.Trim();
    s.Name = req.Name.Trim();
    s.Email = req.Email?.Trim() ?? "";
    s.Phone = req.Phone?.Trim() ?? "";
    await db.SaveChangesAsync(ct);
    return Results.Ok(s);
});

app.MapPut("/api/resources/{id:guid}", async (Guid id, ResourceCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var r = await db.WorkshopResources.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (r is null) return Results.NotFound();
    r.SiteId = req.SiteId ?? r.SiteId;
    r.Name = req.Name.Trim();
    r.Kind = req.Kind;
    r.MaxLoadKg = req.MaxLoadKg;
    r.MaxVehicleHeightM = req.MaxVehicleHeightM;
    r.SupportsEv = req.SupportsEv;
    await db.SaveChangesAsync(ct);
    return Results.Ok(r);
});


app.MapPut("/api/reminders/{id:guid}", async (Guid id, ReminderCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var r = await db.Reminders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (r is null) return Results.NotFound();
    r.CustomerId = req.CustomerId;
    r.VehicleId = req.VehicleId;
    r.Type = req.Type.Trim();
    r.Subject = req.Subject.Trim();
    r.DueAt = req.DueAt;
    r.PreferredChannel = req.PreferredChannel;
    await db.SaveChangesAsync(ct);
    return Results.Ok(r);
});

app.MapPost("/api/reminders/{id:guid}/cancel", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var r = await db.Reminders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (r is null) return Results.NotFound();
    r.Status = ReminderStatus.Cancelled;
    await db.SaveChangesAsync(ct);
    return Results.Ok(r);
});

app.MapPut("/api/loaners/{id:guid}", async (Guid id, LoanerCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var l = await db.LoanerVehicles.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (l is null) return Results.NotFound();
    l.SiteId = req.SiteId ?? l.SiteId;
    l.Number = req.Number.Trim();
    l.LicensePlate = req.LicensePlate.Trim().ToUpperInvariant();
    l.VehicleName = req.VehicleName.Trim();
    l.Mileage = req.Mileage;
    l.FuelOrChargeLevel = req.FuelOrChargeLevel?.Trim() ?? "";
    await db.SaveChangesAsync(ct);
    return Results.Ok(l);
});

app.MapPost("/api/loaner-bookings/{id:guid}/cancel", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var b = await db.LoanerBookings.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (b is null) return Results.NotFound();
    if (b.Status == LoanerBookingStatus.Returned) return Results.Conflict(new { error = "Eine bereits zurückgegebene Buchung kann nicht storniert werden." });
    b.Status = LoanerBookingStatus.Cancelled;
    await db.SaveChangesAsync(ct);
    return Results.Ok(b);
});

app.MapPost("/api/purchase-orders/{id:guid}/cancel", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var po = await db.PurchaseOrders.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (po is null) return Results.NotFound();
    if (po.Status == PurchaseOrderStatus.Received) return Results.Conflict(new { error = "Eine vollständig eingegangene Bestellung kann nicht storniert werden." });
    po.Status = PurchaseOrderStatus.Cancelled;
    await db.SaveChangesAsync(ct);
    return Results.Ok(po);
});

app.MapGet("/api/communications", async (Guid? customerId, Guid? vehicleId, Guid? workOrderId, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = db.CommunicationLogs.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (customerId is not null) q = q.Where(x => x.CustomerId == customerId.Value);
    if (vehicleId is not null) q = q.Where(x => x.VehicleId == vehicleId.Value);
    if (workOrderId is not null) q = q.Where(x => x.WorkOrderId == workOrderId.Value);
    return Results.Ok(await q.OrderByDescending(x => x.OccurredAt).Take(500).ToListAsync(ct));
});

app.MapPost("/api/communications", async (CommunicationCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var log = new CommunicationLog
    {
        TenantId = tenantId,
        CustomerId = req.CustomerId,
        VehicleId = req.VehicleId,
        WorkOrderId = req.WorkOrderId,
        Channel = req.Channel,
        Subject = req.Subject.Trim(),
        Body = req.Body?.Trim() ?? "",
        Direction = string.IsNullOrWhiteSpace(req.Direction) ? "outbound" : req.Direction.Trim(),
        OccurredAt = DateTimeOffset.UtcNow
    };
    db.CommunicationLogs.Add(log);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/communications/{log.Id}", log);
});

app.MapGet("/api/checklists/runs", async (Guid? workOrderId, Guid? vehicleId, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = db.ChecklistRuns.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (workOrderId is not null) q = q.Where(x => x.WorkOrderId == workOrderId.Value);
    if (vehicleId is not null) q = q.Where(x => x.VehicleId == vehicleId.Value);
    return Results.Ok(await q.OrderByDescending(x => x.StartedAt).Take(250).ToListAsync(ct));
});

app.MapPost("/api/checklists/templates", async (ChecklistTemplateWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (string.IsNullOrWhiteSpace(req.Name)) return Results.BadRequest(new { error = "Name fehlt." });
    var t = new ChecklistTemplate { TenantId = tenantId, Name = req.Name.Trim(), Context = req.Context?.Trim() ?? "intake", Active = true };
    db.ChecklistTemplates.Add(t);
    foreach (var f in req.Fields.OrderBy(x => x.SortOrder))
        db.ChecklistFields.Add(new ChecklistField { TenantId = tenantId, ChecklistTemplateId = t.Id, Label = f.Label.Trim(), Type = f.Type, SortOrder = f.SortOrder, Required = f.Required });
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/checklists/templates/{t.Id}", t);
});

app.MapPut("/api/checklists/templates/{id:guid}", async (Guid id, ChecklistTemplateWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var t = await db.ChecklistTemplates.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (t is null) return Results.NotFound();
    t.Name = req.Name.Trim();
    t.Context = req.Context?.Trim() ?? "intake";
    var old = await db.ChecklistFields.Where(x => x.ChecklistTemplateId == id && x.TenantId == tenantId && !x.IsDeleted).ToListAsync(ct);
    foreach (var f in old) f.IsDeleted = true;
    foreach (var f in req.Fields.OrderBy(x => x.SortOrder))
        db.ChecklistFields.Add(new ChecklistField { TenantId = tenantId, ChecklistTemplateId = t.Id, Label = f.Label.Trim(), Type = f.Type, SortOrder = f.SortOrder, Required = f.Required });
    await db.SaveChangesAsync(ct);
    return Results.Ok(t);
});


app.MapGet("/api/finance/open-items", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var today = DateOnly.FromDateTime(DateTime.UtcNow);
    var invoices = await db.Invoices.AsNoTracking()
        .Where(x => x.TenantId == tenantId && !x.IsDeleted &&
                    x.Status != InvoiceStatus.Paid && x.Status != InvoiceStatus.Cancelled && x.Status != InvoiceStatus.Credited &&
                    x.GrossTotal - x.PaidTotal > 0m)
        .OrderBy(x => x.DueDate)
        .ToListAsync(ct);

    var customerIds = invoices.Select(x => x.CustomerId).Distinct().ToList();
    var vehicleIds = invoices.Select(x => x.VehicleId).Where(x => x.HasValue).Select(x => x!.Value).Distinct().ToList();
    var customers = await db.Customers.AsNoTracking().Where(x => x.TenantId == tenantId && customerIds.Contains(x.Id)).ToDictionaryAsync(x => x.Id, ct);
    var vehicles = await db.Vehicles.AsNoTracking().Where(x => x.TenantId == tenantId && vehicleIds.Contains(x.Id)).ToDictionaryAsync(x => x.Id, ct);
    var invoiceIds = invoices.Select(x => x.Id).ToList();
    var dunnings = await db.AuditEntries.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.EntityType == "Invoice" && x.EntityId.HasValue && invoiceIds.Contains(x.EntityId.Value) && x.Action == "dunning-notice" && !x.IsDeleted)
        .ToListAsync(ct);

    return Results.Ok(invoices.Select(i =>
    {
        var daysOverdue = Math.Max(0, today.DayNumber - i.DueDate.DayNumber);
        var customer = customers.GetValueOrDefault(i.CustomerId);
        Vehicle? vehicle = i.VehicleId.HasValue ? vehicles.GetValueOrDefault(i.VehicleId.Value) : null;
        var notices = dunnings.Where(x => x.EntityId == i.Id).OrderBy(x => x.CreatedAt).ToList();
        return new
        {
            invoice = i,
            customerName = customer?.DisplayName ?? "",
            vehiclePlate = vehicle?.LicensePlate ?? "",
            openGross = i.GrossTotal - i.PaidTotal,
            daysOverdue,
            dunningLevel = notices.Count,
            lastDunningAt = notices.LastOrDefault()?.CreatedAt
        };
    }));
});

app.MapPost("/api/finance/invoices/{id:guid}/dunning", async (Guid id, DunningCreate req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var invoice = await db.Invoices.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (invoice is null) return Results.NotFound();
    if (invoice.Status is InvoiceStatus.Paid or InvoiceStatus.Cancelled or InvoiceStatus.Credited)
        return Results.Conflict(new { error = "Für diesen Beleg kann keine Mahnung erstellt werden." });

    var level = await db.AuditEntries.CountAsync(x => x.TenantId == tenantId && x.EntityType == "Invoice" && x.EntityId == id && x.Action == "dunning-notice" && !x.IsDeleted, ct) + 1;
    invoice.Status = InvoiceStatus.Overdue;
    var audit = new AuditEntry
    {
        TenantId = tenantId,
        Actor = "staging-user",
        Action = "dunning-notice",
        EntityType = "Invoice",
        EntityId = invoice.Id,
        NewJson = System.Text.Json.JsonSerializer.Serialize(new
        {
            level,
            fee = req.Fee,
            note = req.Note ?? "",
            openGross = invoice.GrossTotal - invoice.PaidTotal,
            dueDate = invoice.DueDate
        })
    };
    db.AuditEntries.Add(audit);
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { invoiceId = invoice.Id, level, fee = req.Fee, createdAt = audit.CreatedAt });
});

app.MapGet("/api/finance/datev", async (int? year, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var targetYear = year ?? DateTime.UtcNow.Year;
    var from = new DateOnly(targetYear, 1, 1);
    var to = new DateOnly(targetYear, 12, 31);
    var invoices = await db.Invoices.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.IssueDate >= from && x.IssueDate <= to && !x.IsDeleted)
        .OrderBy(x => x.IssueDate).ThenBy(x => x.Number).ToListAsync(ct);

    var customerIds = invoices.Select(x => x.CustomerId).Distinct().ToList();
    var customers = await db.Customers.AsNoTracking()
        .Where(x => x.TenantId == tenantId && customerIds.Contains(x.Id))
        .ToDictionaryAsync(x => x.Id, ct);

    static string Csv(string? value) => "\"" + (value ?? "").Replace("\"", "\"\"") + "\"";
    var sb = new StringBuilder();
    sb.AppendLine("Belegdatum;Belegnummer;Kundennummer;Kunde;Netto;USt;Brutto;Bezahlt;Status");
    foreach (var i in invoices)
    {
        var cu = customers.GetValueOrDefault(i.CustomerId);
        sb.Append(i.IssueDate.ToString("dd.MM.yyyy")).Append(';')
          .Append(Csv(i.Number)).Append(';')
          .Append(Csv(cu?.CustomerNumber)).Append(';')
          .Append(Csv(cu?.DisplayName)).Append(';')
          .Append(i.NetTotal.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture)).Append(';')
          .Append(i.VatTotal.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture)).Append(';')
          .Append(i.GrossTotal.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture)).Append(';')
          .Append(i.PaidTotal.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture)).Append(';')
          .Append(i.Status).AppendLine();
    }
    return Results.Text(sb.ToString(), "text/csv; charset=utf-8");
});

app.MapGet("/api/personnel/qualifications", async (Guid? employeeId, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = db.EmployeeQualifications.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (employeeId.HasValue) q = q.Where(x => x.EmployeeId == employeeId.Value);
    return Results.Ok(await q.OrderBy(x => x.Name).ToListAsync(ct));
});

app.MapPost("/api/personnel/qualifications", async (QualificationWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    if (!await db.Employees.AnyAsync(x => x.Id == req.EmployeeId && x.TenantId == tenantId && !x.IsDeleted, ct))
        return Results.BadRequest(new { error = "Mitarbeiter nicht gefunden." });
    var q = new EmployeeQualification { TenantId = tenantId, EmployeeId = req.EmployeeId, Name = req.Name.Trim(), Level = req.Level, ValidUntil = req.ValidUntil };
    db.EmployeeQualifications.Add(q);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/personnel/qualifications/{q.Id}", q);
});

app.MapPut("/api/personnel/qualifications/{id:guid}", async (Guid id, QualificationWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = await db.EmployeeQualifications.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (q is null) return Results.NotFound();
    q.EmployeeId = req.EmployeeId;
    q.Name = req.Name.Trim();
    q.Level = req.Level;
    q.ValidUntil = req.ValidUntil;
    await db.SaveChangesAsync(ct);
    return Results.Ok(q);
});

app.MapDelete("/api/personnel/qualifications/{id:guid}", async (Guid id, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = await db.EmployeeQualifications.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (q is null) return Results.NotFound();
    q.IsDeleted = true;
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { id, deleted = true });
});

app.MapGet("/api/personnel/vacation-balances", async (int? year, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var targetYear = year ?? DateTime.UtcNow.Year;
    var employees = await db.Employees.AsNoTracking().Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).OrderBy(x => x.Name).ToListAsync(ct);
    var from = new DateOnly(targetYear, 1, 1);
    var to = new DateOnly(targetYear, 12, 31);
    var absences = await db.Absences.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.Type == AbsenceType.Vacation && x.Approved && x.From <= to && x.To >= from && !x.IsDeleted)
        .ToListAsync(ct);

    int BusinessDays(DateOnly a, DateOnly b)
    {
        var start = a < from ? from : a;
        var end = b > to ? to : b;
        var count = 0;
        for (var d = start; d <= end; d = d.AddDays(1))
            if (d.DayOfWeek is not DayOfWeek.Saturday and not DayOfWeek.Sunday) count++;
        return count;
    }

    return Results.Ok(employees.Select(e =>
    {
        var used = absences.Where(a => a.EmployeeId == e.Id).Sum(a => BusinessDays(a.From, a.To));
        return new { employeeId = e.Id, e.Name, e.AnnualVacationDays, used, remaining = e.AnnualVacationDays - used, year = targetYear };
    }));
});

app.MapGet("/api/admin/company", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var tenant = await db.Tenants.AsNoTracking().FirstAsync(x => x.Id == tenantId, ct);
    return Results.Ok(tenant);
});

app.MapPut("/api/admin/company", async (CompanyWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var t = await db.Tenants.FirstAsync(x => x.Id == tenantId, ct);
    t.Name = req.Name.Trim();
    t.LegalName = req.LegalName?.Trim() ?? "";
    t.TaxNumber = req.TaxNumber?.Trim() ?? "";
    t.VatId = req.VatId?.Trim() ?? "";
    t.Email = req.Email?.Trim() ?? "";
    t.Phone = req.Phone?.Trim() ?? "";
    t.PrimaryColor = req.PrimaryColor?.Trim() ?? "#1976D2";
    await db.SaveChangesAsync(ct);
    return Results.Ok(t);
});

app.MapPost("/api/admin/sites", async (SiteWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var s = new Site
    {
        TenantId = tenantId, Name = req.Name.Trim(), Street = req.Street?.Trim() ?? "",
        PostalCode = req.PostalCode?.Trim() ?? "", City = req.City?.Trim() ?? "",
        State = req.State?.Trim() ?? "Brandenburg", CountryCode = req.CountryCode?.Trim().ToUpperInvariant() ?? "DE", Active = req.Active
    };
    db.Sites.Add(s);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/admin/sites/{s.Id}", s);
});

app.MapPut("/api/admin/sites/{id:guid}", async (Guid id, SiteWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var s = await db.Sites.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (s is null) return Results.NotFound();
    s.Name = req.Name.Trim();
    s.Street = req.Street?.Trim() ?? "";
    s.PostalCode = req.PostalCode?.Trim() ?? "";
    s.City = req.City?.Trim() ?? "";
    s.State = req.State?.Trim() ?? "Brandenburg";
    s.CountryCode = req.CountryCode?.Trim().ToUpperInvariant() ?? "DE";
    s.Active = req.Active;
    await db.SaveChangesAsync(ct);
    return Results.Ok(s);
});

app.MapGet("/api/admin/number-sequences", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.NumberSequences.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.Key).ToListAsync(ct));
});

app.MapPut("/api/admin/number-sequences/{id:guid}", async (Guid id, NumberSequenceWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var n = await db.NumberSequences.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (n is null) return Results.NotFound();
    n.Prefix = req.Prefix?.Trim() ?? "";
    n.Suffix = req.Suffix?.Trim() ?? "";
    n.Padding = Math.Clamp(req.Padding, 1, 12);
    n.ResetYearly = req.ResetYearly;
    if (req.NextValue.HasValue && req.NextValue.Value > 0) n.NextValue = req.NextValue.Value;
    await db.SaveChangesAsync(ct);
    return Results.Ok(n);
});

app.MapGet("/api/admin/audit", async (string? entityType, int? limit, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = db.AuditEntries.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (!string.IsNullOrWhiteSpace(entityType)) q = q.Where(x => x.EntityType == entityType);
    var take = Math.Clamp(limit ?? 250, 1, 1000);
    return Results.Ok(await q.OrderByDescending(x => x.CreatedAt).Take(take).ToListAsync(ct));
});

app.MapGet("/api/admin/custom-fields", async (string? entityType, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var q = db.CustomFieldDefinitions.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted);
    if (!string.IsNullOrWhiteSpace(entityType)) q = q.Where(x => x.EntityType == entityType);
    return Results.Ok(await q.OrderBy(x => x.EntityType).ThenBy(x => x.Label).ToListAsync(ct));
});

app.MapPost("/api/admin/custom-fields", async (CustomFieldWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var d = new CustomFieldDefinition
    {
        TenantId = tenantId, EntityType = req.EntityType.Trim(), Key = req.Key.Trim(),
        Label = req.Label.Trim(), FieldType = req.FieldType?.Trim() ?? "text", Required = req.Required,
        OptionsJson = string.IsNullOrWhiteSpace(req.OptionsJson) ? "[]" : req.OptionsJson
    };
    db.CustomFieldDefinitions.Add(d);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/admin/custom-fields/{d.Id}", d);
});

app.MapPut("/api/admin/custom-fields/{id:guid}", async (Guid id, CustomFieldWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var d = await db.CustomFieldDefinitions.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (d is null) return Results.NotFound();
    d.EntityType = req.EntityType.Trim();
    d.Key = req.Key.Trim();
    d.Label = req.Label.Trim();
    d.FieldType = req.FieldType?.Trim() ?? "text";
    d.Required = req.Required;
    d.OptionsJson = string.IsNullOrWhiteSpace(req.OptionsJson) ? "[]" : req.OptionsJson;
    await db.SaveChangesAsync(ct);
    return Results.Ok(d);
});

app.MapGet("/api/admin/document-templates", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    return Results.Ok(await db.DocumentTemplates.AsNoTracking().Where(x => x.TenantId == tenantId && !x.IsDeleted).OrderBy(x => x.Name).ToListAsync(ct));
});

app.MapPost("/api/admin/document-templates", async (DocumentTemplateWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var d = new DocumentTemplate
    {
        TenantId = tenantId, SiteId = req.SiteId, Kind = req.Kind, Name = req.Name.Trim(),
        DefinitionJson = string.IsNullOrWhiteSpace(req.DefinitionJson) ? "{}" : req.DefinitionJson, Active = req.Active
    };
    db.DocumentTemplates.Add(d);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/admin/document-templates/{d.Id}", d);
});

app.MapPut("/api/admin/document-templates/{id:guid}", async (Guid id, DocumentTemplateWrite req, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var d = await db.DocumentTemplates.FirstOrDefaultAsync(x => x.Id == id && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (d is null) return Results.NotFound();
    d.SiteId = req.SiteId;
    d.Kind = req.Kind;
    d.Name = req.Name.Trim();
    d.DefinitionJson = string.IsNullOrWhiteSpace(req.DefinitionJson) ? "{}" : req.DefinitionJson;
    d.Active = req.Active;
    await db.SaveChangesAsync(ct);
    return Results.Ok(d);
});

app.MapGet("/api/reports/productivity", async (DateOnly? from, DateOnly? to, ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var start = from ?? DateOnly.FromDateTime(DateTime.UtcNow.AddDays(-30));
    var end = to ?? DateOnly.FromDateTime(DateTime.UtcNow);
    var fromDt = new DateTimeOffset(start.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero);
    var toDt = new DateTimeOffset(end.AddDays(1).ToDateTime(TimeOnly.MinValue), TimeSpan.Zero);
    var employees = await db.Employees.AsNoTracking().Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).OrderBy(x => x.Name).ToListAsync(ct);
    var times = await db.TimeEntries.AsNoTracking().Where(x => x.TenantId == tenantId && x.StartedAt >= fromDt && x.StartedAt < toDt && !x.IsDeleted).ToListAsync(ct);
    var orderIds = times.Select(x => x.WorkOrderId).Distinct().ToList();
    var lines = await db.WorkOrderLines.AsNoTracking().Where(x => x.TenantId == tenantId && orderIds.Contains(x.WorkOrderId) && x.Type == LineType.Labor && !x.IsDeleted).ToListAsync(ct);

    return Results.Ok(employees.Select(e =>
    {
        var entries = times.Where(x => x.EmployeeId == e.Id).ToList();
        var actualHours = entries.Where(x => x.EndedAt.HasValue).Sum(x => (x.EndedAt!.Value - x.StartedAt).TotalHours);
        var relatedOrders = entries.Select(x => x.WorkOrderId).Distinct().ToList();
        var soldHours = lines.Where(x => relatedOrders.Contains(x.WorkOrderId)).Sum(x => x.Quantity);
        return new
        {
            employeeId = e.Id,
            e.Name,
            e.RoleName,
            actualHours = Math.Round(actualHours, 2),
            soldHours,
            efficiencyPercent = actualHours <= 0 ? 0m : Math.Round((decimal)soldHours / (decimal)actualHours * 100m, 1),
            hourlyRate = e.ProductiveHourlyRate
        };
    }));
});


app.MapGet("/api/quotes", async (ErpDbContext db, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var docs = await db.DocumentRecords.AsNoTracking()
        .Where(x => x.TenantId == tenantId && x.Kind == DocumentKind.Quote && x.RelatedEntityType == "WorkOrder" && x.RelatedEntityId.HasValue && !x.IsDeleted)
        .OrderByDescending(x => x.CreatedAt).Take(250).ToListAsync(ct);
    var orderIds = docs.Select(x => x.RelatedEntityId!.Value).Distinct().ToList();
    var orders = await db.WorkOrders.AsNoTracking().Where(x => x.TenantId == tenantId && orderIds.Contains(x.Id) && !x.IsDeleted).ToDictionaryAsync(x => x.Id, ct);
    var lines = await db.WorkOrderLines.AsNoTracking().Where(x => x.TenantId == tenantId && orderIds.Contains(x.WorkOrderId) && !x.IsDeleted).ToListAsync(ct);
    var customerIds = orders.Values.Select(x => x.CustomerId).Distinct().ToList();
    var vehicleIds = orders.Values.Select(x => x.VehicleId).Distinct().ToList();
    var customers = await db.Customers.AsNoTracking().Where(x => x.TenantId == tenantId && customerIds.Contains(x.Id)).ToDictionaryAsync(x => x.Id, ct);
    var vehicles = await db.Vehicles.AsNoTracking().Where(x => x.TenantId == tenantId && vehicleIds.Contains(x.Id)).ToDictionaryAsync(x => x.Id, ct);

    return Results.Ok(docs.Select(d =>
    {
        var o = orders.GetValueOrDefault(d.RelatedEntityId!.Value);
        if (o is null) return null;
        var ol = lines.Where(x => x.WorkOrderId == o.Id).ToList();
        var net = ol.Sum(x => x.NetTotal);
        var gross = ol.Sum(x => x.NetTotal * (1m + x.VatRate / 100m));
        return new
        {
            quoteId = d.Id,
            quoteNumber = d.FileName,
            workOrder = o,
            customerName = customers.GetValueOrDefault(o.CustomerId)?.DisplayName ?? "",
            vehiclePlate = vehicles.GetValueOrDefault(o.VehicleId)?.LicensePlate ?? "",
            netTotal = Math.Round(net, 2),
            grossTotal = Math.Round(gross, 2),
            converted = !o.Number.StartsWith("KV-")
        };
    }).Where(x => x is not null));
});

app.MapPost("/api/quotes", async (QuoteCreate req, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var siteId = req.SiteId ?? await db.Sites.Where(x => x.TenantId == tenantId && x.Active && !x.IsDeleted).Select(x => x.Id).FirstAsync(ct);
    if (!await db.Customers.AnyAsync(x => x.Id == req.CustomerId && x.TenantId == tenantId && !x.IsDeleted, ct))
        return Results.BadRequest(new { error = "Kunde nicht gefunden." });
    if (!await db.Vehicles.AnyAsync(x => x.Id == req.VehicleId && x.CustomerId == req.CustomerId && x.TenantId == tenantId && !x.IsDeleted, ct))
        return Results.BadRequest(new { error = "Fahrzeug passt nicht zum Kunden." });

    var quoteNumber = await numbers.NextAsync(tenantId, siteId, "quote", "KV-", 5, true, ct);
    var order = new WorkOrder
    {
        TenantId = tenantId, SiteId = siteId, CustomerId = req.CustomerId, VehicleId = req.VehicleId,
        Number = quoteNumber, Status = WorkOrderStatus.Draft,
        CustomerRequest = req.CustomerRequest?.Trim() ?? "", Diagnosis = req.Note?.Trim() ?? ""
    };
    db.WorkOrders.Add(order);
    var doc = new DocumentRecord
    {
        TenantId = tenantId, SiteId = siteId, Kind = DocumentKind.Quote, FileName = quoteNumber,
        MimeType = "application/vnd.workshop-manager.quote", StorageKey = "",
        RelatedEntityType = "WorkOrder", RelatedEntityId = order.Id, SizeBytes = 0
    };
    db.DocumentRecords.Add(doc);
    await db.SaveChangesAsync(ct);
    return Results.Created($"/api/quotes/{doc.Id}", new { quoteId = doc.Id, quoteNumber, workOrder = order });
});

app.MapPost("/api/quotes/{quoteId:guid}/convert", async (Guid quoteId, ErpDbContext db, NumberSequenceService numbers, CancellationToken ct) =>
{
    var tenantId = await TenantId(db, ct);
    var doc = await db.DocumentRecords.FirstOrDefaultAsync(x => x.Id == quoteId && x.TenantId == tenantId && x.Kind == DocumentKind.Quote && !x.IsDeleted, ct);
    if (doc?.RelatedEntityId is null) return Results.NotFound();
    var order = await db.WorkOrders.FirstOrDefaultAsync(x => x.Id == doc.RelatedEntityId.Value && x.TenantId == tenantId && !x.IsDeleted, ct);
    if (order is null) return Results.NotFound();
    if (!order.Number.StartsWith("KV-")) return Results.Conflict(new { error = "Kostenvoranschlag wurde bereits in einen Auftrag umgewandelt." });

    var oldNumber = order.Number;
    var newNumber = await numbers.NextAsync(tenantId, order.SiteId, "work-order", "AU-", 5, true, ct);

    var quoteLines = await db.WorkOrderLines
        .Where(x => x.TenantId == tenantId && x.WorkOrderId == order.Id && x.InventoryItemId.HasValue && !x.IsDeleted)
        .ToListAsync(ct);
    var itemIds = quoteLines.Select(x => x.InventoryItemId!.Value).Distinct().ToList();
    var items = await db.InventoryItems
        .Where(x => x.TenantId == tenantId && itemIds.Contains(x.Id) && !x.IsDeleted)
        .ToDictionaryAsync(x => x.Id, ct);

    foreach (var line in quoteLines)
    {
        var item = items.GetValueOrDefault(line.InventoryItemId!.Value);
        if (item is null) return Results.Conflict(new { error = $"Artikel {line.ItemNumber} ist nicht mehr im Lagerstamm vorhanden." });
        if (item.Stock < line.Quantity)
            return Results.Conflict(new { error = $"Bestand für {item.ItemNumber} reicht nicht aus. Verfügbar: {item.Stock}, benötigt: {line.Quantity}." });
    }

    order.Number = newNumber;
    order.Status = WorkOrderStatus.Scheduled;

    foreach (var line in quoteLines)
    {
        var item = items[line.InventoryItemId!.Value];
        item.Stock -= line.Quantity;
        db.StockMovements.Add(new StockMovement
        {
            TenantId = tenantId,
            InventoryItemId = item.Id,
            SiteId = order.SiteId,
            Type = StockMovementType.Consumption,
            Quantity = line.Quantity,
            Reference = $"KV {oldNumber} → Auftrag {newNumber}"
        });
    }

    db.AuditEntries.Add(new AuditEntry
    {
        TenantId = tenantId, Actor = "staging-user", Action = "quote-converted",
        EntityType = "WorkOrder", EntityId = order.Id,
        OldJson = System.Text.Json.JsonSerializer.Serialize(new { number = oldNumber }),
        NewJson = System.Text.Json.JsonSerializer.Serialize(new { number = newNumber, quote = doc.FileName })
    });
    await db.SaveChangesAsync(ct);
    return Results.Ok(new { quoteId, quoteNumber = doc.FileName, workOrder = order });
});

app.Run();

record LoginRequest(string Username, string Password);
record CustomerCreate(string DisplayName, string? CompanyName, string? FirstName, string? LastName, string? Email, string? Phone, string? Mobile, string? Street, string? PostalCode, string? City, string? Notes);
record VehicleCreate(Guid CustomerId, string LicensePlate, string? Vin, string? Make, string? Model, string? Type, string? Hsn, string? Tsn, DateOnly? FirstRegistration, int? Mileage, DateOnly? NextHu, DateOnly? NextService);
record WorkOrderCreate(Guid? SiteId, Guid CustomerId, Guid VehicleId, string? CustomerRequest, string? Diagnosis, DateTimeOffset? PromisedAt);
record WorkOrderUpdate(string? CustomerRequest, string? Diagnosis, DateTimeOffset? PromisedAt, int? MileageIn, string? FuelOrChargeLevel);
record WorkOrderLineUpdate(LineType Type, string? ItemNumber, string Description, decimal Quantity, decimal UnitNet, decimal VatRate, decimal DiscountPercent, bool ApprovedByCustomer);
record AppointmentCreate(Guid? SiteId, Guid CustomerId, Guid VehicleId, Guid? ResourceId, Guid? EmployeeId, DateTimeOffset StartsAt, DateTimeOffset EndsAt, string Subject, string? CustomerRequest);
record IntakeRequest(int? MileageIn, string? FuelOrChargeLevel, string? CustomerRequest);
record TransitionRequest(WorkOrderStatus Status);
record InventoryLineCreate(Guid InventoryItemId, decimal Quantity, decimal? UnitNet, decimal? VatRate, decimal? DiscountPercent, bool ApprovedByCustomer);
record WorkOrderLineCreate(LineType Type, string? ItemNumber, string Description, decimal Quantity, decimal UnitNet, decimal VatRate, decimal DiscountPercent, Guid? InventoryItemId, Guid? EmployeeId);
record ApprovalCreate(decimal OfferedGross, string? Channel);
record ApprovalResponse(ApprovalStatus Status, string? Note);
record TimeStart(Guid WorkOrderId, Guid EmployeeId, string? Activity);
record InventoryItemCreate(string ItemNumber, string? Ean, string? Manufacturer, string Description, decimal PurchaseNet, decimal SaleNet, decimal Stock, decimal MinimumStock, string? StorageLocation, Guid? PreferredSupplierId);
record StockMovementCreate(Guid SiteId, StockMovementType Type, decimal Quantity, string? Reference);
record TireSetCreate(Guid CustomerId, Guid VehicleId, string StorageNumber, TireSeason Season, string BrandModel, string Size, string? Dot, decimal FrontLeftMm, decimal FrontRightMm, decimal RearLeftMm, decimal RearRightMm, TireCondition Condition, string StorageLocation, bool HasTpms);
record AbsenceCreate(Guid EmployeeId, AbsenceType Type, DateOnly From, DateOnly To, string? Reason, bool Approved, bool AffectsCapacity);
record InvoiceReverseRequest(string Kind, string? Reason);
record PaymentCreate(decimal Amount, PaymentMethod Method, string? Reference);
record SupplierCreate(string? SupplierNumber, string Name, string? Email, string? Phone);
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
record CommunicationCreate(Guid CustomerId, Guid? VehicleId, Guid? WorkOrderId, CommunicationChannel Channel, string Subject, string? Body, string? Direction);
record ChecklistFieldWrite(string Label, ChecklistFieldType Type, int SortOrder, bool Required);
record ChecklistTemplateWrite(string Name, string? Context, List<ChecklistFieldWrite> Fields);
record QuoteCreate(Guid? SiteId, Guid CustomerId, Guid VehicleId, string? CustomerRequest, string? Note);
record DunningCreate(decimal Fee, string? Note);
record QualificationWrite(Guid EmployeeId, string Name, int Level, DateOnly? ValidUntil);
record CompanyWrite(string Name, string? LegalName, string? TaxNumber, string? VatId, string? Email, string? Phone, string? PrimaryColor);
record SiteWrite(string Name, string? Street, string? PostalCode, string? City, string? State, string? CountryCode, bool Active);
record NumberSequenceWrite(string? Prefix, string? Suffix, int Padding, bool ResetYearly, long? NextValue);
record CustomFieldWrite(string EntityType, string Key, string Label, string? FieldType, bool Required, string? OptionsJson);
record DocumentTemplateWrite(Guid? SiteId, DocumentKind Kind, string Name, string? DefinitionJson, bool Active);
record LoanerCreate(Guid? SiteId, string Number, string LicensePlate, string VehicleName, int Mileage, string? FuelOrChargeLevel);
record LoanerBookingCreate(Guid LoanerVehicleId, Guid CustomerId, Guid? WorkOrderId, DateTimeOffset From, DateTimeOffset To);
record LoanerHandover(int? Mileage, string? FuelOrChargeLevel, string? Damage);
record ReminderStatusUpdate(ReminderStatus Status);
record ChecklistRunCreate(Guid ChecklistTemplateId, Guid? WorkOrderId, Guid? VehicleId, Guid? EmployeeId);
record ChecklistAnswerInput(Guid FieldId, string? ValueJson);
record ChecklistComplete(List<ChecklistAnswerInput> Answers);
