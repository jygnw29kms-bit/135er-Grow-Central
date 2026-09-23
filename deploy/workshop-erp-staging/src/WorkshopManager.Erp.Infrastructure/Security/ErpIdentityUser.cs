using Microsoft.AspNetCore.Identity;

namespace WorkshopManager.Erp.Infrastructure.Security;

public sealed class ErpIdentityUser : IdentityUser<Guid>
{
    public Guid TenantId { get; set; }
    public Guid? SiteId { get; set; }
    public string DisplayName { get; set; } = "";
    public bool Active { get; set; } = true;
}
