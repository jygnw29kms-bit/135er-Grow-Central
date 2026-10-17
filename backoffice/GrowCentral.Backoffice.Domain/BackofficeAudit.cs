namespace GrowCentral.Backoffice.Domain;

public enum AuditAction
{
    Created,
    Changed,
    ReviewRequested,
    Approved,
    Finalized,
    Sent,
    Settled,
    Cancelled,
    CorrectionCreated,
    Corrected,
    Archived,
    Exported,
    PeriodLocked,
    PeriodReopened
}

public sealed record AuditEvent(
    Guid Id,
    DateTimeOffset OccurredAtUtc,
    string ActorId,
    AuditAction Action,
    string EntityType,
    string EntityId,
    int EntityVersion,
    string? Reason,
    string? CorrelationId,
    string? IdempotencyKey,
    string PayloadHash);

public sealed record NumberSequenceDefinition(
    string Key,
    string Prefix,
    int Year,
    int Padding = 6);

public static class DocumentNumberFormatter
{
    public static string Format(NumberSequenceDefinition definition, long value)
    {
        if (value <= 0) throw new ArgumentOutOfRangeException(nameof(value));
        if (definition.Padding is < 1 or > 12) throw new ArgumentOutOfRangeException(nameof(definition));
        var serial = value.ToString().PadLeft(definition.Padding, '0');
        return $"{definition.Prefix}-{definition.Year}-{serial}";
    }
}

public interface IBusinessDocumentRepository
{
    Task<BusinessDocument?> GetAsync(Guid id, CancellationToken cancellationToken = default);
    Task AddAsync(BusinessDocument document, CancellationToken cancellationToken = default);
    Task SaveAsync(BusinessDocument document, int expectedVersion, CancellationToken cancellationToken = default);
}

public interface IAuditStore
{
    Task AppendAsync(AuditEvent auditEvent, CancellationToken cancellationToken = default);
}

public interface INumberSequenceStore
{
    Task<long> NextAsync(string sequenceKey, int year, CancellationToken cancellationToken = default);
}
