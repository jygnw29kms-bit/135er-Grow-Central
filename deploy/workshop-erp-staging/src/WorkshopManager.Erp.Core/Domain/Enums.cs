namespace WorkshopManager.Erp.Core.Domain;

public enum WorkOrderStatus { Draft, Scheduled, Arrived, Intake, Diagnosis, ApprovalPending, Approved, InProgress, QualityControl, Ready, Invoiced, Closed, Cancelled }
public enum AppointmentStatus { Requested, Confirmed, Arrived, Converted, Cancelled, NoShow }
public enum LineType { Labor, Part, Material, Fee, Discount, Text }
public enum InvoiceStatus { Draft, Issued, PartiallyPaid, Paid, Overdue, Cancelled, Credited }
public enum PaymentMethod { Cash, Card, BankTransfer, DirectDebit, Other }
public enum PurchaseOrderStatus { Draft, Ordered, PartiallyReceived, Received, Cancelled }
public enum StockMovementType { Receipt, Consumption, Return, Adjustment, Transfer, Reservation, Release }
public enum ApprovalStatus { Pending, Approved, Rejected, CallbackRequested, Expired }
public enum AbsenceType { Vacation, Sick, Training, School, OvertimeComp, SpecialLeave, ParentalLeave, BusinessTrip, Other }
public enum TireSeason { Summer, Winter, AllSeason }
public enum TireCondition { Good, Monitor, Replace }
public enum ResourceKind { Lift, Pit, DiagnosticBay, AlignmentBay, AcStation, TireStation, Parking, ReceptionBay, LoanCar, Tool, Other }
