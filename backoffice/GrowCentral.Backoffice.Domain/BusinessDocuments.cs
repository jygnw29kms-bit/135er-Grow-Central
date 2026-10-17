namespace GrowCentral.Backoffice.Domain;

public enum PartyType { Business, Consumer, Internal, Authority, Employee }
public enum BusinessDocumentStatus { Draft, ReviewRequired, Approved, Finalized, Sent, Settled, Cancelled, Corrected, Archived }
public enum BusinessDocumentCategory { Sales, Billing, Dunning, Complaints, Purchasing, Contracts, Privacy, Employment, Authorities, Internal }
public enum BusinessDocumentKind {
    CustomerInquiryReply, Quote, OrderConfirmation, ChangeOrder, DeliveryNote, ServiceRecord, AcceptanceReport,
    Invoice, AdvanceInvoice, FinalInvoice, InvoiceCorrection, PaymentReminder, FirstDunning, FinalDunning, InstallmentAgreement, BalanceConfirmation,
    ComplaintAcknowledgement, CureNotice, ComplaintRejection, WithdrawalConfirmation, WithdrawalInformation, CustomerTerminationConfirmation, ExtraordinaryTermination,
    PurchaseOrder, SupplierDelayNotice, SupplierDefectNotice, SupplierInvoiceDispute,
    ServiceAgreement, WorkAgreement, NonDisclosureAgreement, ServiceLevelAgreement, SoftwareTerminationConfirmation,
    PrivacyNotice, DataAccessAcknowledgement, DeletionResponse, DataProcessingAgreement, DataBreachReport, ImprintChecklist,
    EmploymentAgreement, VacationRequest, EmploymentWarning, EmploymentTermination,
    TaxAuthorityResponse, DeadlineExtensionRequest, FileNote, ApprovalMemo, AccountingProcedureDocumentation
}

public sealed record DocumentFieldDefinition(string Key, string Label, bool Required, string? Format = null);

public sealed record BusinessDocumentTemplateDefinition(
    string Code,
    BusinessDocumentKind Kind,
    BusinessDocumentCategory Category,
    string Title,
    IReadOnlySet<PartyType> AllowedParties,
    IReadOnlyList<DocumentFieldDefinition> Fields,
    bool LegalReviewRequired = false,
    bool AccountingRelevant = false,
    bool ImmutableAfterFinalization = false,
    string? LegalReference = null);

public sealed record BusinessDocumentLink(Guid TargetDocumentId, string Relation);

public sealed class BusinessDocument
{
    private readonly List<BusinessDocumentLink> _links = [];

    public Guid Id { get; init; } = Guid.NewGuid();
    public required string TemplateCode { get; init; }
    public required string Number { get; init; }
    public required PartyType PartyType { get; init; }
    public BusinessDocumentStatus Status { get; private set; } = BusinessDocumentStatus.Draft;
    public int Version { get; private set; } = 1;
    public DateTimeOffset CreatedAtUtc { get; init; } = DateTimeOffset.UtcNow;
    public required string CreatedBy { get; init; }
    public DateTimeOffset? FinalizedAtUtc { get; private set; }
    public string? FinalizedBy { get; private set; }
    public Dictionary<string, string?> Values { get; } = new(StringComparer.OrdinalIgnoreCase);
    public IReadOnlyList<BusinessDocumentLink> Links => _links;

    public bool IsContentLocked => Status is BusinessDocumentStatus.Finalized
        or BusinessDocumentStatus.Sent
        or BusinessDocumentStatus.Settled
        or BusinessDocumentStatus.Cancelled
        or BusinessDocumentStatus.Corrected
        or BusinessDocumentStatus.Archived;

    public void MarkReviewRequired() => Transition(BusinessDocumentStatus.ReviewRequired, BusinessDocumentStatus.Draft);
    public void Approve() => Transition(BusinessDocumentStatus.Approved, BusinessDocumentStatus.Draft, BusinessDocumentStatus.ReviewRequired);

    public void FinalizeDocument(string actor)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(actor);
        Transition(BusinessDocumentStatus.Finalized, BusinessDocumentStatus.Draft, BusinessDocumentStatus.Approved);
        FinalizedAtUtc = DateTimeOffset.UtcNow;
        FinalizedBy = actor;
    }

    public void MarkSent() => Transition(BusinessDocumentStatus.Sent, BusinessDocumentStatus.Finalized);
    public void MarkSettled() => Transition(BusinessDocumentStatus.Settled, BusinessDocumentStatus.Finalized, BusinessDocumentStatus.Sent);
    public void MarkCorrected() => Transition(BusinessDocumentStatus.Corrected, BusinessDocumentStatus.Finalized, BusinessDocumentStatus.Sent, BusinessDocumentStatus.Settled);
    public void MarkCancelled() => Transition(BusinessDocumentStatus.Cancelled, BusinessDocumentStatus.Finalized, BusinessDocumentStatus.Sent);
    public void Archive() => Transition(BusinessDocumentStatus.Archived, BusinessDocumentStatus.Finalized, BusinessDocumentStatus.Sent, BusinessDocumentStatus.Settled, BusinessDocumentStatus.Cancelled, BusinessDocumentStatus.Corrected);

    public void SetValue(string key, string? value)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(key);
        EnsureContentMutable();
        Values[key] = value;
        Version++;
    }

    public void AddLink(Guid targetDocumentId, string relation)
    {
        if (targetDocumentId == Guid.Empty) throw new ArgumentException("Zieldokument fehlt.", nameof(targetDocumentId));
        ArgumentException.ThrowIfNullOrWhiteSpace(relation);
        EnsureContentMutable();
        if (_links.Any(x => x.TargetDocumentId == targetDocumentId && string.Equals(x.Relation, relation, StringComparison.OrdinalIgnoreCase)))
            return;
        _links.Add(new(targetDocumentId, relation.Trim()));
        Version++;
    }

    private void EnsureContentMutable()
    {
        if (IsContentLocked)
            throw new InvalidOperationException("Finalisierte oder abgeschlossene Geschäftsdokumente dürfen nicht still überschrieben werden. Korrektur-/Stornobeleg erzeugen.");
    }

    private void Transition(BusinessDocumentStatus target, params BusinessDocumentStatus[] allowedFrom)
    {
        if (!allowedFrom.Contains(Status))
            throw new InvalidOperationException($"Ungültiger Dokumentstatuswechsel {Status} -> {target}.");
        Status = target;
        Version++;
    }
}

public sealed record ValidationIssue(string Code, string Message, bool IsBlocking = true);
public sealed record ValidationResult(bool IsValid, IReadOnlyList<ValidationIssue> Issues);
