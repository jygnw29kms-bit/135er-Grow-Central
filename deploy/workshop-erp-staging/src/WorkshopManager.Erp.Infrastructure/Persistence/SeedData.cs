using Microsoft.EntityFrameworkCore;
using WorkshopManager.Erp.Core.Domain;

namespace WorkshopManager.Erp.Infrastructure.Persistence;

public static class SeedData
{
    public static async Task EnsureDemoAsync(ErpDbContext db, CancellationToken ct = default)
    {
        await db.Database.EnsureCreatedAsync(ct);
        if (await db.Tenants.AnyAsync(ct)) return;

        var tenant = new Tenant { Name = "Musterwerkstatt", LegalName = "Musterwerkstatt GmbH" };
        var site = new Site { TenantId = tenant.Id, Name = "Hauptbetrieb", City = "Falkensee", State = "Brandenburg" };
        var customer = new Customer { TenantId = tenant.Id, CustomerNumber = "K-10001", DisplayName = "Max Weber", FirstName = "Max", LastName = "Weber", City = "Falkensee" };
        var vehicle = new Vehicle { TenantId = tenant.Id, CustomerId = customer.Id, LicensePlate = "HVL-WM 1028", Vin = "WVWZZZDEMO0001028", Make = "Volkswagen", Model = "Golf VIII", Mileage = 48210 };
        var employee = new Employee { TenantId = tenant.Id, SiteId = site.Id, PersonnelNumber = "MA-001", Name = "Alex Berger", RoleName = "Werkstattleitung", ProductiveHourlyRate = 109m };
        var lift = new WorkshopResource { TenantId = tenant.Id, SiteId = site.Id, Name = "Bühne 1", Kind = ResourceKind.Lift, MaxLoadKg = 3500, SupportsEv = true };
        var supplier = new Supplier { TenantId = tenant.Id, SupplierNumber = "L-001", Name = "Teilehandel Demo" };
        var oilFilter = new InventoryItem { TenantId = tenant.Id, ItemNumber = "OF-221", Description = "Ölfilter", Stock = 8, MinimumStock = 4, PurchaseNet = 6.20m, SaleNet = 14.90m, PreferredSupplierId = supplier.Id, StorageLocation = "A-03-04" };

        var appt = new Appointment
        {
            TenantId = tenant.Id, SiteId = site.Id, CustomerId = customer.Id, VehicleId = vehicle.Id,
            ResourceId = lift.Id, EmployeeId = employee.Id, StartsAt = DateTimeOffset.UtcNow.Date.AddHours(8),
            EndsAt = DateTimeOffset.UtcNow.Date.AddHours(10), Status = AppointmentStatus.Confirmed,
            Subject = "Inspektion + Ölservice", CustomerRequest = "Inspektion nach Herstellervorgabe"
        };

        db.AddRange(tenant, site, customer, vehicle, employee, lift, supplier, oilFilter, appt);
        await db.SaveChangesAsync(ct);
    }
}
