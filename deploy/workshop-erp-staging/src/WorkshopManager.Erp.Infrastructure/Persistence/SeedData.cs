using Microsoft.EntityFrameworkCore;
using WorkshopManager.Erp.Core.Domain;

namespace WorkshopManager.Erp.Infrastructure.Persistence;

public static class SeedData
{
    private const string RichSeedMarker = "staging-seed-2025-revenue-980900-v1";

    public static async Task EnsureDemoAsync(ErpDbContext db, CancellationToken ct = default)
    {
        await db.Database.EnsureCreatedAsync(ct);

        var tenant = await db.Tenants.FirstOrDefaultAsync(ct);
        if (tenant is null)
        {
            tenant = new Tenant { Name = "Musterwerkstatt", LegalName = "Musterwerkstatt GmbH" };
            db.Tenants.Add(tenant);
            await db.SaveChangesAsync(ct);
        }

        var site = await db.Sites.FirstOrDefaultAsync(x => x.TenantId == tenant.Id, ct);
        if (site is null)
        {
            site = new Site
            {
                TenantId = tenant.Id, Name = "Hauptbetrieb", Street = "Werkstattstraße 12",
                PostalCode = "14612", City = "Falkensee", State = "Brandenburg"
            };
            db.Sites.Add(site);
            await db.SaveChangesAsync(ct);
        }

        await EnsureOperationalDemoAsync(db, tenant, site, ct);
        await EnsureHistoricalRevenue2025Async(db, tenant, site, ct);
    }

    private static async Task EnsureOperationalDemoAsync(ErpDbContext db, Tenant tenant, Site site, CancellationToken ct)
    {
        if (!await db.Customers.AnyAsync(x => x.TenantId == tenant.Id, ct))
        {
            var customer = new Customer
            {
                TenantId = tenant.Id, CustomerNumber = "K-10001", DisplayName = "Max Weber",
                FirstName = "Max", LastName = "Weber", Phone = "03322 555 120",
                Email = "max.weber@example.invalid", PostalCode = "14612", City = "Falkensee"
            };
            var vehicle = new Vehicle
            {
                TenantId = tenant.Id, CustomerId = customer.Id, LicensePlate = "HVL-WM 1028",
                Vin = "WVWZZZDEMO0001028", Make = "Volkswagen", Model = "Golf VIII", Mileage = 48210,
                FirstRegistration = new DateOnly(2022, 5, 16), NextHu = new DateOnly(2027, 5, 1)
            };
            db.AddRange(customer, vehicle);
        }

        if (await db.Employees.CountAsync(x => x.TenantId == tenant.Id, ct) < 6)
        {
            var employees = new[]
            {
                ("MA-001","Alex Berger","Werkstattleitung",40m,119m),
                ("MA-002","Mara König","Serviceberatung",40m,99m),
                ("MA-003","Daniel Krüger","Kfz-Mechatroniker",40m,109m),
                ("MA-004","Sven Hartmann","Kfz-Mechatroniker",40m,109m),
                ("MA-005","Lea Neumann","Diagnosetechnik",38.5m,129m),
                ("MA-006","Nico Brandt","Auszubildender",40m,69m),
                ("MA-007","Sophie Keller","Buchhaltung",35m,89m)
            };
            foreach (var e in employees)
            {
                if (await db.Employees.AnyAsync(x => x.TenantId == tenant.Id && x.PersonnelNumber == e.Item1, ct)) continue;
                db.Employees.Add(new Employee
                {
                    TenantId = tenant.Id, SiteId = site.Id, PersonnelNumber = e.Item1, Name = e.Item2,
                    RoleName = e.Item3, WeeklyHours = e.Item4, ProductiveHourlyRate = e.Item5,
                    AnnualVacationDays = 30, Active = true
                });
            }
        }

        if (await db.WorkshopResources.CountAsync(x => x.TenantId == tenant.Id, ct) < 5)
        {
            var resources = new[]
            {
                ("Bühne 1",ResourceKind.Lift,3500m,true),
                ("Bühne 2",ResourceKind.Lift,3500m,true),
                ("Diagnoseplatz",ResourceKind.DiagnosticBay,0m,true),
                ("Achsvermessung",ResourceKind.AlignmentBay,0m,true),
                ("Reifenplatz",ResourceKind.TireStation,0m,false),
                ("Direktannahme",ResourceKind.ReceptionBay,0m,true)
            };
            foreach (var r in resources)
            {
                if (await db.WorkshopResources.AnyAsync(x => x.TenantId == tenant.Id && x.Name == r.Item1, ct)) continue;
                db.WorkshopResources.Add(new WorkshopResource
                {
                    TenantId = tenant.Id, SiteId = site.Id, Name = r.Item1, Kind = r.Item2,
                    MaxLoadKg = r.Item3 == 0m ? null : r.Item3, SupportsEv = r.Item4, Active = true
                });
            }
        }

        if (!await db.Suppliers.AnyAsync(x => x.TenantId == tenant.Id && x.SupplierNumber == "L-001", ct))
            db.Suppliers.Add(new Supplier { TenantId = tenant.Id, SupplierNumber = "L-001", Name = "Teilehandel Nord", Phone = "030 555 3300" });
        if (!await db.Suppliers.AnyAsync(x => x.TenantId == tenant.Id && x.SupplierNumber == "L-002", ct))
            db.Suppliers.Add(new Supplier { TenantId = tenant.Id, SupplierNumber = "L-002", Name = "Autoteile Brandenburg", Email = "bestellung@example.invalid" });

        await db.SaveChangesAsync(ct);

        var supplier1 = await db.Suppliers.FirstAsync(x => x.TenantId == tenant.Id && x.SupplierNumber == "L-001", ct);
        var inventory = new[]
        {
            ("OF-221","Ölfilter Premium",8m,4m,6.20m,14.90m,"A-03-04"),
            ("5W30-5L","Motoröl 5W-30 5 Liter",18m,8m,29.50m,54.90m,"ÖL-01"),
            ("BR-1042","Bremsbelagsatz Vorderachse",5m,3m,44.00m,89.00m,"B-02-01"),
            ("IF-331","Innenraumfilter Aktivkohle",3m,4m,10.80m,24.90m,"A-04-02"),
            ("WIS-650","Wischerblattsatz 650/450",7m,3m,18.90m,39.90m,"C-01-03"),
            ("BAT-AGM70","AGM Batterie 70 Ah",2m,2m,112.00m,189.00m,"BAT-02")
        };
        foreach (var i in inventory)
        {
            if (await db.InventoryItems.AnyAsync(x => x.TenantId == tenant.Id && x.ItemNumber == i.Item1, ct)) continue;
            db.InventoryItems.Add(new InventoryItem
            {
                TenantId = tenant.Id, ItemNumber = i.Item1, Description = i.Item2, Stock = i.Item3,
                MinimumStock = i.Item4, PurchaseNet = i.Item5, SaleNet = i.Item6,
                StorageLocation = i.Item7, PreferredSupplierId = supplier1.Id
            });
        }
        await db.SaveChangesAsync(ct);

        if (await db.Appointments.CountAsync(x => x.TenantId == tenant.Id, ct) < 5)
        {
            var baseCustomers = await EnsureCurrentCustomersAsync(db, tenant.Id, ct);
            var employees = await db.Employees.Where(x => x.TenantId == tenant.Id && x.Active).OrderBy(x => x.PersonnelNumber).ToListAsync(ct);
            var resources = await db.WorkshopResources.Where(x => x.TenantId == tenant.Id && x.Active).OrderBy(x => x.Name).ToListAsync(ct);

            var subjects = new[] { "Inspektion + Ölservice", "Bremsen prüfen", "HU-Vorbereitung", "Fehlerspeicher / Motorkontrollleuchte", "Räderwechsel", "Klimaanlagenservice", "Geräusch Vorderachse" };
            var requests = new[] { "Inspektion nach Herstellervorgabe", "Bremsen quietschen", "HU im nächsten Monat", "Motorkontrollleuchte sporadisch an", "Winterräder montieren", "Klimaanlage kühlt schwach", "Poltern bei Unebenheiten" };

            for (var i = 0; i < 7; i++)
            {
                var pair = baseCustomers[i % baseCustomers.Count];
                db.Appointments.Add(new Appointment
                {
                    TenantId = tenant.Id, SiteId = site.Id, CustomerId = pair.Customer.Id, VehicleId = pair.Vehicle.Id,
                    ResourceId = resources.Count > 0 ? resources[i % resources.Count].Id : null,
                    EmployeeId = employees.Count > 0 ? employees[i % employees.Count].Id : null,
                    StartsAt = DateTimeOffset.UtcNow.Date.AddHours(8 + i),
                    EndsAt = DateTimeOffset.UtcNow.Date.AddHours(9 + i),
                    Status = AppointmentStatus.Confirmed, Subject = subjects[i], CustomerRequest = requests[i]
                });
            }
            await db.SaveChangesAsync(ct);
        }

        var openOrderCount = await db.WorkOrders.CountAsync(x => x.TenantId == tenant.Id &&
            x.Status != WorkOrderStatus.Closed && x.Status != WorkOrderStatus.Cancelled, ct);
        if (openOrderCount < 4)
        {
            var currentPairs = await EnsureCurrentCustomersAsync(db, tenant.Id, ct);
            var openCases = new[]
            {
                (0, WorkOrderStatus.Diagnosis, "Motorlauf unruhig / Motorkontrollleuchte", "Fehlerspeicher P0302, Zündaussetzer Zylinder 2"),
                (1, WorkOrderStatus.ApprovalPending, "Bremsgeräusch Vorderachse", "Bremsscheiben und Beläge Vorderachse verschlissen"),
                (2, WorkOrderStatus.InProgress, "Inspektion nach Herstellervorgabe", "Inspektion läuft, Öl und Filter erneuert"),
                (3, WorkOrderStatus.QualityControl, "Klimaanlage ohne ausreichende Kühlleistung", "Kältemittelservice und Dichtigkeitsprüfung abgeschlossen")
            };

            var seq = 90001;
            foreach (var item in openCases)
            {
                var pair = currentPairs[item.Item1];
                if (await db.WorkOrders.AnyAsync(x => x.TenantId == tenant.Id && x.Number == $"AU-2026-{seq:00000}", ct))
                {
                    seq++;
                    continue;
                }

                var order = new WorkOrder
                {
                    TenantId = tenant.Id, SiteId = site.Id, CustomerId = pair.Customer.Id, VehicleId = pair.Vehicle.Id,
                    Number = $"AU-2026-{seq:00000}", Status = item.Item2, CustomerRequest = item.Item3,
                    Diagnosis = item.Item4, MileageIn = pair.Vehicle.Mileage,
                    FuelOrChargeLevel = "½", PromisedAt = DateTimeOffset.UtcNow.Date.AddHours(16 + item.Item1)
                };
                db.WorkOrders.Add(order);
                db.WorkOrderLines.Add(new WorkOrderLine
                {
                    TenantId = tenant.Id, WorkOrderId = order.Id, Type = LineType.Labor,
                    Description = "Diagnose / Arbeitszeit", Quantity = 1.5m + item.Item1 * 0.5m,
                    UnitNet = 109m, VatRate = 19m, ApprovedByCustomer = item.Item2 >= WorkOrderStatus.Approved
                });
                if (item.Item2 == WorkOrderStatus.ApprovalPending)
                {
                    db.CustomerApprovals.Add(new CustomerApproval
                    {
                        TenantId = tenant.Id, WorkOrderId = order.Id, Status = ApprovalStatus.Pending,
                        OfferedGross = 489.00m, Channel = "Link", Token = Convert.ToHexString(Guid.NewGuid().ToByteArray())
                    });
                }
                seq++;
            }
            await db.SaveChangesAsync(ct);
        }
    }

    private static async Task<List<(Customer Customer, Vehicle Vehicle)>> EnsureCurrentCustomersAsync(ErpDbContext db, Guid tenantId, CancellationToken ct)
    {
        var data = new[]
        {
            ("K-11001","Sabine Hoffmann","HVL-SH 841","Audi","A4 Avant","WAUZZZDEMO11001",68420),
            ("K-11002","Thomas Richter","B-TR 4212","BMW","320d Touring","WBADEMO00011002",91800),
            ("K-11003","Nina Schulz","HVL-NS 503","Škoda","Octavia","TMBDEMO00011003",52210),
            ("K-11004","Marco Lehmann","P-MK 772","Ford","Transit Custom","WF0DEMO00011004",122300),
            ("K-11005","Anja Wolf","B-AW 1906","Mercedes-Benz","A 200","WDDDEMO00011005",36100),
            ("K-11006","Peter Krüger","HVL-PK 77","Volkswagen","T-Roc","WVGDEMO00011006",44780),
            ("K-11007","Miriam Lange","B-ML 820","Opel","Astra","W0LDEMO00011007",73500),
            ("K-11008","Dennis Bauer","HVL-DB 315","Hyundai","Tucson","KMHDEMO00011008",28120)
        };

        foreach (var d in data)
        {
            if (await db.Customers.AnyAsync(x => x.TenantId == tenantId && x.CustomerNumber == d.Item1, ct)) continue;
            var c = new Customer
            {
                TenantId = tenantId, CustomerNumber = d.Item1, DisplayName = d.Item2,
                Phone = "03322 55" + d.Item1[^3..], Email = d.Item1.ToLowerInvariant() + "@example.invalid",
                PostalCode = "14612", City = "Falkensee"
            };
            var v = new Vehicle
            {
                TenantId = tenantId, CustomerId = c.Id, LicensePlate = d.Item3, Make = d.Item4, Model = d.Item5,
                Vin = d.Item6, Mileage = d.Item7, FirstRegistration = new DateOnly(2021 + (d.Item7 % 4), 4, 15),
                NextHu = new DateOnly(2027, 4, 1)
            };
            db.AddRange(c, v);
        }
        await db.SaveChangesAsync(ct);

        var result = new List<(Customer, Vehicle)>();
        foreach (var d in data)
        {
            var c = await db.Customers.FirstAsync(x => x.TenantId == tenantId && x.CustomerNumber == d.Item1, ct);
            var v = await db.Vehicles.FirstAsync(x => x.TenantId == tenantId && x.CustomerId == c.Id, ct);
            result.Add((c, v));
        }
        return result;
    }

    private static async Task EnsureHistoricalRevenue2025Async(ErpDbContext db, Tenant tenant, Site site, CancellationToken ct)
    {
        if (await db.AuditEntries.AnyAsync(x => x.TenantId == tenant.Id && x.Action == RichSeedMarker, ct))
            return;

        var names = new[]
        {
            "Autohaus Westend GmbH","Berliner Pflegedienst mobil GmbH","Klaus Mertens","Heike Sommer","Jan Peters","Miriam Scholz",
            "Bau & Service Havel GmbH","Tobias Franke","Svenja Kramer","Oliver Roth","Kurierdienst Nordwest GmbH","Petra Winter",
            "Daniel Vogt","Julia Fuchs","Elektro Havel GmbH","Kathrin Seidel","Andreas Horn","Malerbetrieb König GmbH",
            "Stefan Busch","Nadine Werner","Hausmeisterservice Falkensee","Martin Beck","Claudia Simon","Robert Hahn"
        };
        var makes = new[] { "Volkswagen","Audi","BMW","Mercedes-Benz","Škoda","Ford","Opel","Hyundai" };
        var models = new[] { "Golf","A4","3er","C-Klasse","Octavia","Transit","Astra","Tucson" };

        var pairs = new List<(Customer Customer, Vehicle Vehicle)>();
        for (var i = 0; i < names.Length; i++)
        {
            var number = $"K-25{i + 1:000}";
            var c = await db.Customers.FirstOrDefaultAsync(x => x.TenantId == tenant.Id && x.CustomerNumber == number, ct);
            if (c is null)
            {
                c = new Customer
                {
                    TenantId = tenant.Id, CustomerNumber = number, DisplayName = names[i],
                    Phone = $"03322 60{i + 10:000}", Email = $"kunde25{i + 1:000}@example.invalid",
                    PostalCode = i % 3 == 0 ? "13589" : "14612", City = i % 3 == 0 ? "Berlin" : "Falkensee"
                };
                db.Customers.Add(c);
                await db.SaveChangesAsync(ct);
            }

            var plate = i % 3 == 0 ? $"B-ERP {2100 + i}" : $"HVL-ERP {310 + i}";
            var v = await db.Vehicles.FirstOrDefaultAsync(x => x.TenantId == tenant.Id && x.LicensePlate == plate, ct);
            if (v is null)
            {
                v = new Vehicle
                {
                    TenantId = tenant.Id, CustomerId = c.Id, LicensePlate = plate,
                    Vin = $"DEMO2025VIN{i + 1:000000000}", Make = makes[i % makes.Length], Model = models[i % models.Length],
                    Mileage = 25000 + i * 4200, FirstRegistration = new DateOnly(2019 + i % 6, 3 + i % 8, 12),
                    NextHu = new DateOnly(2027, 3 + i % 8, 1)
                };
                db.Vehicles.Add(v);
                await db.SaveChangesAsync(ct);
            }
            pairs.Add((c, v));
        }

        decimal[] monthlyNet = [72000m,76000m,79000m,81000m,82500m,84000m,86500m,80000m,79500m,81500m,84000m,94900m];
        decimal[] offsets = [-2200m,-1600m,-900m,-300m,300m,900m,1600m,2200m];
        var invoiceSeq = 1;

        for (var month = 1; month <= 12; month++)
        {
            var baseValue = monthlyNet[month - 1] / 8m;
            for (var ix = 0; ix < 8; ix++)
            {
                var pair = pairs[(month * 5 + ix * 3) % pairs.Count];
                var net = baseValue + offsets[ix];
                var vat = Math.Round(net * 0.19m, 2);
                var gross = net + vat;
                var issueDate = new DateOnly(2025, month, Math.Min(4 + ix * 3, DateTime.DaysInMonth(2025, month)));
                var order = new WorkOrder
                {
                    TenantId = tenant.Id, SiteId = site.Id, CustomerId = pair.Customer.Id, VehicleId = pair.Vehicle.Id,
                    Number = $"AU-2025-{invoiceSeq:00000}", Status = WorkOrderStatus.Closed,
                    CustomerRequest = ix % 3 == 0 ? "Inspektion und Verschleißprüfung" : ix % 3 == 1 ? "Reparatur laut Diagnose" : "Wartung und Zusatzarbeiten",
                    Diagnosis = "Arbeiten abgeschlossen und Qualitätskontrolle durchgeführt.",
                    MileageIn = (pair.Vehicle.Mileage ?? 40000) - (13 - month) * 700,
                    MileageOut = (pair.Vehicle.Mileage ?? 40000) - (13 - month) * 700 + 4,
                    CompletedAt = issueDate.ToDateTime(new TimeOnly(16, 30), DateTimeKind.Utc)
                };
                db.WorkOrders.Add(order);

                var labor = Math.Round(net * 0.36m, 2);
                var parts = Math.Round(net * 0.54m, 2);
                var material = net - labor - parts;
                db.WorkOrderLines.AddRange(
                    new WorkOrderLine { TenantId = tenant.Id, WorkOrderId = order.Id, Type = LineType.Labor, Description = "Arbeitsleistung Werkstatt", Quantity = 1, UnitNet = labor, VatRate = 19m, ApprovedByCustomer = true },
                    new WorkOrderLine { TenantId = tenant.Id, WorkOrderId = order.Id, Type = LineType.Part, Description = "Ersatzteile und Komponenten", Quantity = 1, UnitNet = parts, VatRate = 19m, ApprovedByCustomer = true },
                    new WorkOrderLine { TenantId = tenant.Id, WorkOrderId = order.Id, Type = LineType.Material, Description = "Betriebs- und Hilfsstoffe", Quantity = 1, UnitNet = material, VatRate = 19m, ApprovedByCustomer = true }
                );

                var invoice = new Invoice
                {
                    TenantId = tenant.Id, SiteId = site.Id, CustomerId = pair.Customer.Id, VehicleId = pair.Vehicle.Id,
                    WorkOrderId = order.Id, Number = $"RE-2025-{invoiceSeq:00000}", Status = InvoiceStatus.Paid,
                    IssueDate = issueDate, DueDate = issueDate.AddDays(14), NetTotal = net, VatTotal = vat,
                    GrossTotal = gross, PaidTotal = gross
                };
                db.Invoices.Add(invoice);
                db.InvoiceLines.AddRange(
                    new InvoiceLine { TenantId = tenant.Id, InvoiceId = invoice.Id, Type = LineType.Labor, Description = "Arbeitsleistung Werkstatt", Quantity = 1, UnitNet = labor, VatRate = 19m },
                    new InvoiceLine { TenantId = tenant.Id, InvoiceId = invoice.Id, Type = LineType.Part, Description = "Ersatzteile und Komponenten", Quantity = 1, UnitNet = parts, VatRate = 19m },
                    new InvoiceLine { TenantId = tenant.Id, InvoiceId = invoice.Id, Type = LineType.Material, Description = "Betriebs- und Hilfsstoffe", Quantity = 1, UnitNet = material, VatRate = 19m }
                );
                db.Payments.Add(new Payment
                {
                    TenantId = tenant.Id, InvoiceId = invoice.Id, Amount = gross,
                    PaidAt = new DateTimeOffset(issueDate.AddDays(6).ToDateTime(new TimeOnly(10, 15), DateTimeKind.Utc)),
                    Method = ix % 4 == 0 ? PaymentMethod.Card : PaymentMethod.BankTransfer,
                    Reference = $"ZAHLUNG-{invoiceSeq:00000}"
                });
                invoiceSeq++;
            }
        }

        db.AuditEntries.Add(new AuditEntry
        {
            TenantId = tenant.Id, Actor = "staging-seed", Action = RichSeedMarker,
            EntityType = "StagingDataset", NewJson = "{\"year\":2025,\"netRevenue\":980900.00,\"invoiceCount\":96}"
        });
        await db.SaveChangesAsync(ct);

        var exactRevenue = await db.Invoices
            .Where(x => x.TenantId == tenant.Id && x.IssueDate >= new DateOnly(2025,1,1) && x.IssueDate <= new DateOnly(2025,12,31) && x.Status != InvoiceStatus.Cancelled)
            .SumAsync(x => x.NetTotal, ct);
        if (exactRevenue != 980900m)
            throw new InvalidOperationException($"Staging-Umsatz 2025 stimmt nicht: {exactRevenue:N2} statt 980.900,00.");
    }
}
