namespace WorkshopManager.Erp.Infrastructure.Security;

public static class PermissionCatalog
{
    public static readonly string[] All =
    [
        "customers.read", "customers.write",
        "vehicles.read", "vehicles.write",
        "appointments.read", "appointments.write",
        "orders.read", "orders.write",
        "inventory.read", "inventory.write",
        "purchasing.read", "purchasing.write",
        "tires.read", "tires.write",
        "personnel.read", "personnel.write",
        "billing.read", "billing.write",
        "reports.read",
        "resources.read", "resources.write",
        "crm.read", "crm.write",
        "loaners.read", "loaners.write",
        "admin.security", "admin.settings", "admin.import", "admin.backup"
    ];
}
