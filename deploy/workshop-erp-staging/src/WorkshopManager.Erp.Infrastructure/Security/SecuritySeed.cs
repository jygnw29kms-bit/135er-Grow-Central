using Microsoft.EntityFrameworkCore;
using WorkshopManager.Erp.Core.Domain;
using WorkshopManager.Erp.Infrastructure.Persistence;

namespace WorkshopManager.Erp.Infrastructure.Security;

public static class SecuritySeed
{
    public static async Task EnsureAdminAsync(ErpDbContext db, Guid tenantId, Guid userProfileId, CancellationToken ct = default)
    {
        foreach (var key in PermissionCatalog.All)
        {
            if (!await db.PermissionDefinitions.AnyAsync(x => x.Key == key && !x.IsDeleted, ct))
            {
                var module = key.Split('.', 2)[0];
                db.PermissionDefinitions.Add(new PermissionDefinition
                {
                    Key = key,
                    Module = module,
                    Description = key
                });
            }
        }
        await db.SaveChangesAsync(ct);

        var adminRole = await db.RoleDefinitions.FirstOrDefaultAsync(x => x.TenantId == tenantId && x.Name == "Administrator" && !x.IsDeleted, ct);
        if (adminRole is null)
        {
            adminRole = new RoleDefinition
            {
                TenantId = tenantId,
                Name = "Administrator",
                Description = "Vollzugriff auf alle ERP-Module",
                SystemRole = true
            };
            db.RoleDefinitions.Add(adminRole);
            await db.SaveChangesAsync(ct);
        }

        if (!await db.UserRoleAssignments.AnyAsync(x => x.TenantId == tenantId && x.UserProfileId == userProfileId && x.RoleDefinitionId == adminRole.Id && !x.IsDeleted, ct))
            db.UserRoleAssignments.Add(new UserRoleAssignment { TenantId = tenantId, UserProfileId = userProfileId, RoleDefinitionId = adminRole.Id });

        var permissionIds = await db.PermissionDefinitions.Where(x => PermissionCatalog.All.Contains(x.Key) && !x.IsDeleted).Select(x => x.Id).ToListAsync(ct);
        var existing = await db.RolePermissions.Where(x => x.TenantId == tenantId && x.RoleDefinitionId == adminRole.Id && !x.IsDeleted).Select(x => x.PermissionDefinitionId).ToListAsync(ct);
        foreach (var id in permissionIds.Except(existing))
            db.RolePermissions.Add(new RolePermission { TenantId = tenantId, RoleDefinitionId = adminRole.Id, PermissionDefinitionId = id, Effect = PermissionEffect.Allow });

        await db.SaveChangesAsync(ct);
    }
}
