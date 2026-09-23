using System.Data;
using Microsoft.EntityFrameworkCore;
using WorkshopManager.Erp.Core.Domain;

namespace WorkshopManager.Erp.Infrastructure.Persistence;

public sealed class NumberSequenceService(ErpDbContext db)
{
    public async Task<string> NextAsync(Guid tenantId, Guid? siteId, string key, string prefix, int padding = 5, bool resetYearly = true, CancellationToken ct = default)
    {
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.Serializable, ct);
        var year = DateTime.UtcNow.Year;

        var seq = await db.NumberSequences
            .FirstOrDefaultAsync(x => x.TenantId == tenantId && x.SiteId == siteId && x.Key == key, ct);

        if (seq is null)
        {
            seq = new NumberSequence
            {
                TenantId = tenantId,
                SiteId = siteId,
                Key = key,
                Prefix = prefix,
                Padding = padding,
                ResetYearly = resetYearly,
                CurrentYear = year,
                NextValue = 1
            };
            db.NumberSequences.Add(seq);
        }

        if (seq.ResetYearly && seq.CurrentYear != year)
        {
            seq.CurrentYear = year;
            seq.NextValue = 1;
        }

        var value = seq.NextValue++;
        seq.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(ct);
        await tx.CommitAsync(ct);

        var number = value.ToString().PadLeft(seq.Padding, '0');
        var yr = seq.ResetYearly ? $"{year}-" : "";
        return $"{seq.Prefix}{yr}{number}{seq.Suffix}";
    }
}
