using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace WorkshopManager.Erp.Core.Domain;

public abstract class Entity
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    public bool IsDeleted { get; set; }
}

public interface ITenantScoped { Guid TenantId { get; set; } }

public class Tenant : Entity
{
    [MaxLength(200)] public string Name { get; set; } = "";
    [MaxLength(200)] public string LegalName { get; set; } = "";
    [MaxLength(40)] public string TaxNumber { get; set; } = "";
    [MaxLength(40)] public string VatId { get; set; } = "";
    [MaxLength(200)] public string Email { get; set; } = "";
    [MaxLength(80)] public string Phone { get; set; } = "";
    public string? LogoPath { get; set; }
    [MaxLength(20)] public string PrimaryColor { get; set; } = "#1976D2";
    public bool Active { get; set; } = true;
}

public class Site : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(160)] public string Name { get; set; } = "";
    [MaxLength(200)] public string Street { get; set; } = "";
    [MaxLength(20)] public string PostalCode { get; set; } = "";
    [MaxLength(100)] public string City { get; set; } = "";
    [MaxLength(100)] public string State { get; set; } = "Brandenburg";
    [MaxLength(2)] public string CountryCode { get; set; } = "DE";
    public bool Active { get; set; } = true;
}

public class Customer : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(30)] public string CustomerNumber { get; set; } = "";
    [MaxLength(200)] public string DisplayName { get; set; } = "";
    [MaxLength(200)] public string CompanyName { get; set; } = "";
    [MaxLength(100)] public string FirstName { get; set; } = "";
    [MaxLength(100)] public string LastName { get; set; } = "";
    [MaxLength(200)] public string Email { get; set; } = "";
    [MaxLength(80)] public string Phone { get; set; } = "";
    [MaxLength(80)] public string Mobile { get; set; } = "";
    [MaxLength(200)] public string Street { get; set; } = "";
    [MaxLength(20)] public string PostalCode { get; set; } = "";
    [MaxLength(100)] public string City { get; set; } = "";
    public string Notes { get; set; } = "";
}

public class Vehicle : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid CustomerId { get; set; }
    [MaxLength(40)] public string LicensePlate { get; set; } = "";
    [MaxLength(40)] public string Vin { get; set; } = "";
    [MaxLength(100)] public string Make { get; set; } = "";
    [MaxLength(100)] public string Model { get; set; } = "";
    [MaxLength(100)] public string Type { get; set; } = "";
    [MaxLength(40)] public string Hsn { get; set; } = "";
    [MaxLength(40)] public string Tsn { get; set; } = "";
    public DateOnly? FirstRegistration { get; set; }
    public int? Mileage { get; set; }
    public DateOnly? NextHu { get; set; }
    public DateOnly? NextService { get; set; }
}

public class Employee : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid? SiteId { get; set; }
    [MaxLength(40)] public string PersonnelNumber { get; set; } = "";
    [MaxLength(160)] public string Name { get; set; } = "";
    [MaxLength(100)] public string RoleName { get; set; } = "";
    public decimal WeeklyHours { get; set; } = 40m;
    public decimal ProductiveHourlyCost { get; set; }
    public decimal ProductiveHourlyRate { get; set; }
    public int AnnualVacationDays { get; set; } = 30;
    public bool Active { get; set; } = true;
}

public class EmployeeQualification : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid EmployeeId { get; set; }
    [MaxLength(160)] public string Name { get; set; } = "";
    public int Level { get; set; } = 1;
    public DateOnly? ValidUntil { get; set; }
}

public class Absence : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid EmployeeId { get; set; }
    public AbsenceType Type { get; set; }
    public DateOnly From { get; set; }
    public DateOnly To { get; set; }
    [MaxLength(500)] public string Reason { get; set; } = "";
    public bool Approved { get; set; }
    public bool AffectsCapacity { get; set; } = true;
}

public class WorkshopResource : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid SiteId { get; set; }
    [MaxLength(120)] public string Name { get; set; } = "";
    public ResourceKind Kind { get; set; }
    public decimal? MaxLoadKg { get; set; }
    public decimal? MaxVehicleHeightM { get; set; }
    public bool SupportsEv { get; set; }
    public bool Active { get; set; } = true;
}

public class Appointment : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid SiteId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid VehicleId { get; set; }
    public Guid? ResourceId { get; set; }
    public Guid? EmployeeId { get; set; }
    public DateTimeOffset StartsAt { get; set; }
    public DateTimeOffset EndsAt { get; set; }
    public AppointmentStatus Status { get; set; } = AppointmentStatus.Requested;
    [MaxLength(200)] public string Subject { get; set; } = "";
    public string CustomerRequest { get; set; } = "";
    public Guid? WorkOrderId { get; set; }
}

public class WorkOrder : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid SiteId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid VehicleId { get; set; }
    public Guid? AppointmentId { get; set; }
    [MaxLength(40)] public string Number { get; set; } = "";
    public WorkOrderStatus Status { get; set; } = WorkOrderStatus.Draft;
    public string CustomerRequest { get; set; } = "";
    public string Diagnosis { get; set; } = "";
    public string InternalNotes { get; set; } = "";
    public int? MileageIn { get; set; }
    public int? MileageOut { get; set; }
    [MaxLength(40)] public string FuelOrChargeLevel { get; set; } = "";
    public DateTimeOffset? PromisedAt { get; set; }
    public DateTimeOffset? CompletedAt { get; set; }
}

public class WorkOrderLine : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid WorkOrderId { get; set; }
    public LineType Type { get; set; }
    [MaxLength(80)] public string ItemNumber { get; set; } = "";
    [MaxLength(500)] public string Description { get; set; } = "";
    public decimal Quantity { get; set; } = 1m;
    public decimal UnitNet { get; set; }
    public decimal VatRate { get; set; } = 19m;
    public decimal DiscountPercent { get; set; }
    public Guid? InventoryItemId { get; set; }
    public Guid? EmployeeId { get; set; }
    public bool ApprovedByCustomer { get; set; }
    [NotMapped] public decimal NetTotal => Math.Round(Quantity * UnitNet * (1m - DiscountPercent / 100m), 2);
}

public class CustomerApproval : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid WorkOrderId { get; set; }
    public ApprovalStatus Status { get; set; } = ApprovalStatus.Pending;
    public decimal OfferedGross { get; set; }
    [MaxLength(100)] public string Channel { get; set; } = "Link";
    [MaxLength(120)] public string Token { get; set; } = "";
    public DateTimeOffset? RespondedAt { get; set; }
    public string ResponseNote { get; set; } = "";
}

public class TimeEntry : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid WorkOrderId { get; set; }
    public Guid EmployeeId { get; set; }
    public DateTimeOffset StartedAt { get; set; }
    public DateTimeOffset? EndedAt { get; set; }
    [MaxLength(160)] public string Activity { get; set; } = "";
    [MaxLength(200)] public string InterruptionReason { get; set; } = "";
}

public class Supplier : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(40)] public string SupplierNumber { get; set; } = "";
    [MaxLength(200)] public string Name { get; set; } = "";
    [MaxLength(200)] public string Email { get; set; } = "";
    [MaxLength(80)] public string Phone { get; set; } = "";
}

public class InventoryItem : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(80)] public string ItemNumber { get; set; } = "";
    [MaxLength(80)] public string Ean { get; set; } = "";
    [MaxLength(160)] public string Manufacturer { get; set; } = "";
    [MaxLength(240)] public string Description { get; set; } = "";
    public decimal PurchaseNet { get; set; }
    public decimal SaleNet { get; set; }
    public decimal Stock { get; set; }
    public decimal MinimumStock { get; set; }
    [MaxLength(120)] public string StorageLocation { get; set; } = "";
    public Guid? PreferredSupplierId { get; set; }
}

public class PurchaseOrder : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid SupplierId { get; set; }
    public Guid SiteId { get; set; }
    [MaxLength(40)] public string Number { get; set; } = "";
    public PurchaseOrderStatus Status { get; set; } = PurchaseOrderStatus.Draft;
    public DateTimeOffset? OrderedAt { get; set; }
    public DateTimeOffset? ExpectedAt { get; set; }
}

public class PurchaseOrderLine : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid PurchaseOrderId { get; set; }
    public Guid InventoryItemId { get; set; }
    public decimal Quantity { get; set; }
    public decimal ReceivedQuantity { get; set; }
    public decimal UnitPurchaseNet { get; set; }
}

public class StockMovement : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid InventoryItemId { get; set; }
    public Guid SiteId { get; set; }
    public StockMovementType Type { get; set; }
    public decimal Quantity { get; set; }
    [MaxLength(200)] public string Reference { get; set; } = "";
}

public class TireSet : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid VehicleId { get; set; }
    [MaxLength(40)] public string StorageNumber { get; set; } = "";
    public TireSeason Season { get; set; }
    [MaxLength(160)] public string BrandModel { get; set; } = "";
    [MaxLength(80)] public string Size { get; set; } = "";
    [MaxLength(20)] public string Dot { get; set; } = "";
    public decimal FrontLeftMm { get; set; }
    public decimal FrontRightMm { get; set; }
    public decimal RearLeftMm { get; set; }
    public decimal RearRightMm { get; set; }
    public TireCondition Condition { get; set; }
    [MaxLength(160)] public string StorageLocation { get; set; } = "";
    public bool HasTpms { get; set; }
    public DateTimeOffset StoredAt { get; set; } = DateTimeOffset.UtcNow;
}

public class Invoice : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid SiteId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid? VehicleId { get; set; }
    public Guid? WorkOrderId { get; set; }
    [MaxLength(40)] public string Number { get; set; } = "";
    public InvoiceStatus Status { get; set; } = InvoiceStatus.Draft;
    public DateOnly IssueDate { get; set; }
    public DateOnly DueDate { get; set; }
    public decimal NetTotal { get; set; }
    public decimal VatTotal { get; set; }
    public decimal GrossTotal { get; set; }
    public decimal PaidTotal { get; set; }
}

public class InvoiceLine : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid InvoiceId { get; set; }
    public LineType Type { get; set; }
    [MaxLength(500)] public string Description { get; set; } = "";
    public decimal Quantity { get; set; }
    public decimal UnitNet { get; set; }
    public decimal VatRate { get; set; } = 19m;
    public decimal DiscountPercent { get; set; }
}

public class Payment : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid InvoiceId { get; set; }
    public DateTimeOffset PaidAt { get; set; } = DateTimeOffset.UtcNow;
    public decimal Amount { get; set; }
    public PaymentMethod Method { get; set; }
    [MaxLength(160)] public string Reference { get; set; } = "";
}

public class AuditEntry : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(160)] public string Actor { get; set; } = "";
    [MaxLength(120)] public string Action { get; set; } = "";
    [MaxLength(120)] public string EntityType { get; set; } = "";
    public Guid? EntityId { get; set; }
    public string OldJson { get; set; } = "";
    public string NewJson { get; set; } = "";
}
