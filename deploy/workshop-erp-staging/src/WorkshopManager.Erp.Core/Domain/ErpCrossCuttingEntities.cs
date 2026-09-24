using System.ComponentModel.DataAnnotations;

namespace WorkshopManager.Erp.Core.Domain;

public enum PermissionEffect { Allow, Deny }
public enum DocumentKind { Quote = 0, WorkOrder = 1, Intake = 2, Approval = 3, Invoice = 4, CreditNote = 5, Checklist = 6, Photo = 7, Attachment = 8, Other = 9, DeliveryNote = 10 }
public enum CommunicationChannel { Email, Sms, Phone, WhatsApp, Letter, InApp }
public enum ReminderStatus { Open, Sent, Completed, Cancelled }
public enum ChecklistFieldType { Checkbox, OkDefect, Text, Number, Measurement, Photo, Signature, Select }
public enum LoanerBookingStatus { Reserved, HandedOut, Returned, Cancelled }

public class UserProfile : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid? SiteId { get; set; }
    [MaxLength(160)] public string ExternalSubject { get; set; } = "";
    [MaxLength(160)] public string DisplayName { get; set; } = "";
    [MaxLength(200)] public string Email { get; set; } = "";
    public bool Active { get; set; } = true;
}

public class RoleDefinition : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(120)] public string Name { get; set; } = "";
    [MaxLength(240)] public string Description { get; set; } = "";
    public bool SystemRole { get; set; }
}

public class PermissionDefinition : Entity
{
    [MaxLength(160)] public string Key { get; set; } = "";
    [MaxLength(120)] public string Module { get; set; } = "";
    [MaxLength(240)] public string Description { get; set; } = "";
}

public class UserRoleAssignment : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid UserProfileId { get; set; }
    public Guid RoleDefinitionId { get; set; }
    public Guid? SiteId { get; set; }
}

public class RolePermission : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid RoleDefinitionId { get; set; }
    public Guid PermissionDefinitionId { get; set; }
    public PermissionEffect Effect { get; set; } = PermissionEffect.Allow;
}

public class UserPermissionOverride : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid UserProfileId { get; set; }
    public Guid PermissionDefinitionId { get; set; }
    public Guid? SiteId { get; set; }
    public PermissionEffect Effect { get; set; }
}

public class NumberSequence : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid? SiteId { get; set; }
    [MaxLength(80)] public string Key { get; set; } = "";
    [MaxLength(40)] public string Prefix { get; set; } = "";
    [MaxLength(40)] public string Suffix { get; set; } = "";
    public long NextValue { get; set; } = 1;
    public int Padding { get; set; } = 5;
    public bool ResetYearly { get; set; } = true;
    public int CurrentYear { get; set; } = DateTime.UtcNow.Year;
}

public class DocumentRecord : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid? SiteId { get; set; }
    public DocumentKind Kind { get; set; }
    [MaxLength(160)] public string FileName { get; set; } = "";
    [MaxLength(120)] public string MimeType { get; set; } = "";
    [MaxLength(500)] public string StorageKey { get; set; } = "";
    [MaxLength(128)] public string Sha256 { get; set; } = "";
    [MaxLength(120)] public string RelatedEntityType { get; set; } = "";
    public Guid? RelatedEntityId { get; set; }
    public long SizeBytes { get; set; }
}

public class DocumentTemplate : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid? SiteId { get; set; }
    public DocumentKind Kind { get; set; }
    [MaxLength(160)] public string Name { get; set; } = "";
    public string DefinitionJson { get; set; } = "{}";
    public bool Active { get; set; } = true;
}

public class CustomFieldDefinition : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(120)] public string EntityType { get; set; } = "";
    [MaxLength(120)] public string Key { get; set; } = "";
    [MaxLength(160)] public string Label { get; set; } = "";
    [MaxLength(40)] public string FieldType { get; set; } = "text";
    public bool Required { get; set; }
    public string OptionsJson { get; set; } = "[]";
}

public class CustomFieldValue : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid DefinitionId { get; set; }
    public Guid EntityId { get; set; }
    public string ValueJson { get; set; } = "null";
}

public class CommunicationLog : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid? VehicleId { get; set; }
    public Guid? WorkOrderId { get; set; }
    public CommunicationChannel Channel { get; set; }
    [MaxLength(240)] public string Subject { get; set; } = "";
    public string Body { get; set; } = "";
    public DateTimeOffset OccurredAt { get; set; } = DateTimeOffset.UtcNow;
    [MaxLength(160)] public string Direction { get; set; } = "outbound";
}

public class Reminder : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid? VehicleId { get; set; }
    [MaxLength(80)] public string Type { get; set; } = "";
    [MaxLength(240)] public string Subject { get; set; } = "";
    public DateTimeOffset DueAt { get; set; }
    public ReminderStatus Status { get; set; } = ReminderStatus.Open;
    public CommunicationChannel PreferredChannel { get; set; } = CommunicationChannel.Email;
}

public class LoanerVehicle : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid SiteId { get; set; }
    [MaxLength(40)] public string Number { get; set; } = "";
    [MaxLength(40)] public string LicensePlate { get; set; } = "";
    [MaxLength(160)] public string VehicleName { get; set; } = "";
    public int Mileage { get; set; }
    [MaxLength(40)] public string FuelOrChargeLevel { get; set; } = "";
    public bool Active { get; set; } = true;
}

public class LoanerBooking : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid LoanerVehicleId { get; set; }
    public Guid CustomerId { get; set; }
    public Guid? WorkOrderId { get; set; }
    public DateTimeOffset From { get; set; }
    public DateTimeOffset To { get; set; }
    public LoanerBookingStatus Status { get; set; } = LoanerBookingStatus.Reserved;
    public int? MileageOut { get; set; }
    public int? MileageIn { get; set; }
    [MaxLength(40)] public string FuelOut { get; set; } = "";
    [MaxLength(40)] public string FuelIn { get; set; } = "";
    public string DamageOut { get; set; } = "";
    public string DamageIn { get; set; } = "";
}

public class ChecklistTemplate : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    [MaxLength(160)] public string Name { get; set; } = "";
    [MaxLength(80)] public string Context { get; set; } = "intake";
    public bool Active { get; set; } = true;
}

public class ChecklistField : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid ChecklistTemplateId { get; set; }
    [MaxLength(160)] public string Label { get; set; } = "";
    public ChecklistFieldType Type { get; set; }
    public int SortOrder { get; set; }
    public bool Required { get; set; }
    public string OptionsJson { get; set; } = "[]";
}

public class ChecklistRun : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid ChecklistTemplateId { get; set; }
    public Guid? WorkOrderId { get; set; }
    public Guid? VehicleId { get; set; }
    public Guid? EmployeeId { get; set; }
    public DateTimeOffset StartedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? CompletedAt { get; set; }
}

public class ChecklistAnswer : Entity, ITenantScoped
{
    public Guid TenantId { get; set; }
    public Guid ChecklistRunId { get; set; }
    public Guid ChecklistFieldId { get; set; }
    public string ValueJson { get; set; } = "null";
}
