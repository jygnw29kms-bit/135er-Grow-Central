using Microsoft.EntityFrameworkCore;
using WorkshopManager.Erp.Core.Domain;

namespace WorkshopManager.Erp.Infrastructure.Persistence;

public sealed class PermissionService(ErpDbContext db)
{
    public async Task<bool> HasAsync(Guid tenantId, Guid userProfileId, string permissionKey, Guid? siteId = null, CancellationToken ct = default)
    {
        var permission = await db.PermissionDefinitions.AsNoTracking()
            .FirstOrDefaultAsync(x => x.Key == permissionKey && !x.IsDeleted, ct);
        if (permission is null) return false;

        var overrides = await db.UserPermissionOverrides.AsNoTracking()
            .Where(x => x.TenantId == tenantId && x.UserProfileId == userProfileId &&
                        x.PermissionDefinitionId == permission.Id && !x.IsDeleted &&
                        (x.SiteId == null || x.SiteId == siteId))
            .ToListAsync(ct);

        if (overrides.Any(x => x.Effect == PermissionEffect.Deny)) return false;
        if (overrides.Any(x => x.Effect == PermissionEffect.Allow)) return true;

        var roleIds = await db.UserRoleAssignments.AsNoTracking()
            .Where(x => x.TenantId == tenantId && x.UserProfileId == userProfileId && !x.IsDeleted &&
                        (x.SiteId == null || x.SiteId == siteId))
            .Select(x => x.RoleDefinitionId)
            .ToListAsync(ct);

        if (roleIds.Count == 0) return false;

        var rolePermissions = await db.RolePermissions.AsNoTracking()
            .Where(x => x.TenantId == tenantId && roleIds.Contains(x.RoleDefinitionId) &&
                        x.PermissionDefinitionId == permission.Id && !x.IsDeleted)
            .ToListAsync(ct);

        if (rolePermissions.Any(x => x.Effect == PermissionEffect.Deny)) return false;
        return rolePermissions.Any(x => x.Effect == PermissionEffect.Allow);
    }
}
