using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using WorkshopManager.Erp.Infrastructure.Security;
using WorkshopManager.Erp.Core.Domain;

namespace WorkshopManager.Erp.Infrastructure.Persistence;

public sealed class ErpDbContext(DbContextOptions<ErpDbContext> options) : IdentityDbContext<ErpIdentityUser, IdentityRole<Guid>, Guid>(options)
{
    public DbSet<Tenant> Tenants => Set<Tenant>();
    public DbSet<Site> Sites => Set<Site>();
    public DbSet<Customer> Customers => Set<Customer>();
    public DbSet<Vehicle> Vehicles => Set<Vehicle>();
    public DbSet<Employee> Employees => Set<Employee>();
    public DbSet<EmployeeQualification> EmployeeQualifications => Set<EmployeeQualification>();
    public DbSet<Absence> Absences => Set<Absence>();
    public DbSet<WorkshopResource> WorkshopResources => Set<WorkshopResource>();
    public DbSet<Appointment> Appointments => Set<Appointment>();
    public DbSet<WorkOrder> WorkOrders => Set<WorkOrder>();
    public DbSet<WorkOrderLine> WorkOrderLines => Set<WorkOrderLine>();
    public DbSet<CustomerApproval> CustomerApprovals => Set<CustomerApproval>();
    public DbSet<TimeEntry> TimeEntries => Set<TimeEntry>();
    public DbSet<Supplier> Suppliers => Set<Supplier>();
    public DbSet<InventoryItem> InventoryItems => Set<InventoryItem>();
    public DbSet<PurchaseOrder> PurchaseOrders => Set<PurchaseOrder>();
    public DbSet<PurchaseOrderLine> PurchaseOrderLines => Set<PurchaseOrderLine>();
    public DbSet<StockMovement> StockMovements => Set<StockMovement>();
    public DbSet<TireSet> TireSets => Set<TireSet>();
    public DbSet<Invoice> Invoices => Set<Invoice>();
    public DbSet<InvoiceLine> InvoiceLines => Set<InvoiceLine>();
    public DbSet<Payment> Payments => Set<Payment>();
    public DbSet<AuditEntry> AuditEntries => Set<AuditEntry>();
    public DbSet<UserProfile> UserProfiles => Set<UserProfile>();
    public DbSet<RoleDefinition> RoleDefinitions => Set<RoleDefinition>();
    public DbSet<PermissionDefinition> PermissionDefinitions => Set<PermissionDefinition>();
    public DbSet<UserRoleAssignment> UserRoleAssignments => Set<UserRoleAssignment>();
    public DbSet<RolePermission> RolePermissions => Set<RolePermission>();
    public DbSet<UserPermissionOverride> UserPermissionOverrides => Set<UserPermissionOverride>();
    public DbSet<NumberSequence> NumberSequences => Set<NumberSequence>();
    public DbSet<DocumentRecord> DocumentRecords => Set<DocumentRecord>();
    public DbSet<DocumentTemplate> DocumentTemplates => Set<DocumentTemplate>();
    public DbSet<CustomFieldDefinition> CustomFieldDefinitions => Set<CustomFieldDefinition>();
    public DbSet<CustomFieldValue> CustomFieldValues => Set<CustomFieldValue>();
    public DbSet<CommunicationLog> CommunicationLogs => Set<CommunicationLog>();
    public DbSet<Reminder> Reminders => Set<Reminder>();
    public DbSet<LoanerVehicle> LoanerVehicles => Set<LoanerVehicle>();
    public DbSet<LoanerBooking> LoanerBookings => Set<LoanerBooking>();
    public DbSet<ChecklistTemplate> ChecklistTemplates => Set<ChecklistTemplate>();
    public DbSet<ChecklistField> ChecklistFields => Set<ChecklistField>();
    public DbSet<ChecklistRun> ChecklistRuns => Set<ChecklistRun>();
    public DbSet<ChecklistAnswer> ChecklistAnswers => Set<ChecklistAnswer>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        base.OnModelCreating(b);

        b.Entity<Site>().HasIndex(x => new { x.TenantId, x.Name });
        b.Entity<Customer>().HasIndex(x => new { x.TenantId, x.CustomerNumber }).IsUnique();
        b.Entity<Vehicle>().HasIndex(x => new { x.TenantId, x.LicensePlate });
        b.Entity<Vehicle>().HasIndex(x => new { x.TenantId, x.Vin });
        b.Entity<Employee>().HasIndex(x => new { x.TenantId, x.PersonnelNumber }).IsUnique();
        b.Entity<Appointment>().HasIndex(x => new { x.TenantId, x.SiteId, x.StartsAt });
        b.Entity<WorkOrder>().HasIndex(x => new { x.TenantId, x.Number }).IsUnique();
        b.Entity<Supplier>().HasIndex(x => new { x.TenantId, x.SupplierNumber }).IsUnique();
        b.Entity<InventoryItem>().HasIndex(x => new { x.TenantId, x.ItemNumber }).IsUnique();
        b.Entity<PurchaseOrder>().HasIndex(x => new { x.TenantId, x.Number }).IsUnique();
        b.Entity<TireSet>().HasIndex(x => new { x.TenantId, x.StorageNumber }).IsUnique();
        b.Entity<Invoice>().HasIndex(x => new { x.TenantId, x.Number }).IsUnique();
        b.Entity<UserProfile>().HasIndex(x => new { x.TenantId, x.ExternalSubject }).IsUnique();
        b.Entity<RoleDefinition>().HasIndex(x => new { x.TenantId, x.Name }).IsUnique();
        b.Entity<PermissionDefinition>().HasIndex(x => x.Key).IsUnique();
        b.Entity<UserRoleAssignment>().HasIndex(x => new { x.TenantId, x.UserProfileId, x.RoleDefinitionId, x.SiteId }).IsUnique();
        b.Entity<RolePermission>().HasIndex(x => new { x.TenantId, x.RoleDefinitionId, x.PermissionDefinitionId }).IsUnique();
        b.Entity<UserPermissionOverride>().HasIndex(x => new { x.TenantId, x.UserProfileId, x.PermissionDefinitionId, x.SiteId }).IsUnique();
        b.Entity<NumberSequence>().HasIndex(x => new { x.TenantId, x.SiteId, x.Key }).IsUnique();
        b.Entity<CustomFieldDefinition>().HasIndex(x => new { x.TenantId, x.EntityType, x.Key }).IsUnique();
        b.Entity<CustomFieldValue>().HasIndex(x => new { x.TenantId, x.DefinitionId, x.EntityId }).IsUnique();
        b.Entity<LoanerVehicle>().HasIndex(x => new { x.TenantId, x.Number }).IsUnique();
        b.Entity<ChecklistField>().HasIndex(x => new { x.TenantId, x.ChecklistTemplateId, x.SortOrder });

        Money<WorkOrderLine>(b, nameof(WorkOrderLine.UnitNet));
        Money<InventoryItem>(b, nameof(InventoryItem.PurchaseNet));
        Money<InventoryItem>(b, nameof(InventoryItem.SaleNet));
        Money<PurchaseOrderLine>(b, nameof(PurchaseOrderLine.UnitPurchaseNet));
        Money<CustomerApproval>(b, nameof(CustomerApproval.OfferedGross));
        Money<Invoice>(b, nameof(Invoice.NetTotal));
        Money<Invoice>(b, nameof(Invoice.VatTotal));
        Money<Invoice>(b, nameof(Invoice.GrossTotal));
        Money<Invoice>(b, nameof(Invoice.PaidTotal));
        Money<InvoiceLine>(b, nameof(InvoiceLine.UnitNet));
        Money<Payment>(b, nameof(Payment.Amount));

        b.Entity<Vehicle>().HasOne<Customer>().WithMany().HasForeignKey(x => x.CustomerId).OnDelete(DeleteBehavior.Restrict);
        b.Entity<Appointment>().HasOne<Customer>().WithMany().HasForeignKey(x => x.CustomerId).OnDelete(DeleteBehavior.Restrict);
        b.Entity<Appointment>().HasOne<Vehicle>().WithMany().HasForeignKey(x => x.VehicleId).OnDelete(DeleteBehavior.Restrict);
        b.Entity<WorkOrder>().HasOne<Customer>().WithMany().HasForeignKey(x => x.CustomerId).OnDelete(DeleteBehavior.Restrict);
        b.Entity<WorkOrder>().HasOne<Vehicle>().WithMany().HasForeignKey(x => x.VehicleId).OnDelete(DeleteBehavior.Restrict);
        b.Entity<WorkOrderLine>().HasOne<WorkOrder>().WithMany().HasForeignKey(x => x.WorkOrderId).OnDelete(DeleteBehavior.Cascade);
        b.Entity<InvoiceLine>().HasOne<Invoice>().WithMany().HasForeignKey(x => x.InvoiceId).OnDelete(DeleteBehavior.Cascade);
        b.Entity<Payment>().HasOne<Invoice>().WithMany().HasForeignKey(x => x.InvoiceId).OnDelete(DeleteBehavior.Restrict);
    }

    public override Task<int> SaveChangesAsync(CancellationToken ct = default)
    {
        foreach (var e in ChangeTracker.Entries<Entity>().Where(x => x.State == EntityState.Modified))
            e.Entity.UpdatedAt = DateTimeOffset.UtcNow;
        return base.SaveChangesAsync(ct);
    }

    private static void Money<T>(ModelBuilder b, string property) where T : class =>
        b.Entity<T>().Property<decimal>(property).HasPrecision(18, 2);
}
