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
    public List<BusinessDocumentLink> Links { get; } = [];

    public void MarkReviewRequired() => ChangeStatus(BusinessDocumentStatus.ReviewRequired);
    public void Approve() => ChangeStatus(BusinessDocumentStatus.Approved);

    public void FinalizeDocument(string actor)
    {
        if (Status is not (BusinessDocumentStatus.Approved or BusinessDocumentStatus.Draft))
            throw new InvalidOperationException($"Dokument im Status {Status} kann nicht finalisiert werden.");
        Status = BusinessDocumentStatus.Finalized;
        FinalizedAtUtc = DateTimeOffset.UtcNow;
        FinalizedBy = actor;
        Version++;
    }

    public void MarkSent() => ChangeStatus(BusinessDocumentStatus.Sent);
    public void MarkSettled() => ChangeStatus(BusinessDocumentStatus.Settled);
    public void MarkCorrected() => ChangeStatus(BusinessDocumentStatus.Corrected);
    public void Archive() => ChangeStatus(BusinessDocumentStatus.Archived);

    public void SetValue(string key, string? value)
    {
        if (Status is BusinessDocumentStatus.Finalized or BusinessDocumentStatus.Sent or BusinessDocumentStatus.Settled or BusinessDocumentStatus.Archived)
            throw new InvalidOperationException("Finalisierte Geschäftsdokumente dürfen nicht still überschrieben werden. Korrektur-/Stornobeleg erzeugen.");
        Values[key] = value;
        Version++;
    }

    private void ChangeStatus(BusinessDocumentStatus status)
    {
        Status = status;
        Version++;
    }
}

public sealed record ValidationIssue(string Code, string Message, bool IsBlocking = true);
public sealed record ValidationResult(bool IsValid, IReadOnlyList<ValidationIssue> Issues);
