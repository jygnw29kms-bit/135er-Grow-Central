using WorkshopManager.Erp.Core.Domain;

namespace WorkshopManager.Erp.Core.Services;

public sealed class WorkOrderWorkflowService
{
    private static readonly Dictionary<WorkOrderStatus, WorkOrderStatus[]> Allowed = new()
    {
        [WorkOrderStatus.Draft] = [WorkOrderStatus.Scheduled, WorkOrderStatus.Cancelled],
        [WorkOrderStatus.Scheduled] = [WorkOrderStatus.Arrived, WorkOrderStatus.Cancelled],
        [WorkOrderStatus.Arrived] = [WorkOrderStatus.Intake, WorkOrderStatus.Cancelled],
        [WorkOrderStatus.Intake] = [WorkOrderStatus.Diagnosis, WorkOrderStatus.InProgress],
        [WorkOrderStatus.Diagnosis] = [WorkOrderStatus.ApprovalPending, WorkOrderStatus.InProgress],
        [WorkOrderStatus.ApprovalPending] = [WorkOrderStatus.Approved, WorkOrderStatus.Cancelled],
        [WorkOrderStatus.Approved] = [WorkOrderStatus.InProgress],
        [WorkOrderStatus.InProgress] = [WorkOrderStatus.QualityControl, WorkOrderStatus.ApprovalPending],
        [WorkOrderStatus.QualityControl] = [WorkOrderStatus.Ready, WorkOrderStatus.InProgress],
        [WorkOrderStatus.Ready] = [WorkOrderStatus.Invoiced],
        [WorkOrderStatus.Invoiced] = [WorkOrderStatus.Closed],
        [WorkOrderStatus.Closed] = [],
        [WorkOrderStatus.Cancelled] = []
    };

    public void Transition(WorkOrder order, WorkOrderStatus next)
    {
        if (order.Status == next) return;
        if (!Allowed.TryGetValue(order.Status, out var allowed) || !allowed.Contains(next))
            throw new InvalidOperationException($"Statuswechsel {order.Status} -> {next} ist nicht zulässig.");

        order.Status = next;
        order.UpdatedAt = DateTimeOffset.UtcNow;
        if (next == WorkOrderStatus.Ready)
            order.CompletedAt = DateTimeOffset.UtcNow;
    }
}
