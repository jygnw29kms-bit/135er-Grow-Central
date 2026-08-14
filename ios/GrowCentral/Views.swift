import Charts
import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var model: AppModel
    let columns = [GridItem(.adaptive(minimum: 155), spacing: 12)]
    var body: some View {
        ScrollView {
            VStack(spacing: 14) {
                GCTitle(title: "Lokale Zentrale")
                LazyVGrid(columns: columns, spacing: 12) {
                    GCMetric(title: "Geräte online", value: "\(model.onlineCount) / \(model.devices.count)", tint: GCTheme.green)
                    GCMetric(title: "Leistung", value: model.currentPowerW.formatted(.number.precision(.fractionLength(1))) + " W", tint: GCTheme.cyan)
                    GCMetric(title: "Gesamtenergie", value: (model.totalEnergyWh / 1000).formatted(.number.precision(.fractionLength(3))) + " kWh", tint: GCTheme.cyan)
                    GCMetric(title: "Gesamtkosten", value: model.totalCost.formatted(.currency(code: "EUR")), tint: GCTheme.green)
                }
                GCPanel(content: VStack(alignment: .leading, spacing: 10) {
                    HStack { Text("LIVE-STATUS").font(.caption.monospaced()).foregroundStyle(GCTheme.cyan); Spacer(); if model.loading { ProgressView() } }
                    Text(model.lastRefresh.map { "Zuletzt geprüft: \($0.formatted(date: .omitted, time: .standard))" } ?? "Noch nicht geprüft")
                        .font(.caption.monospaced()).foregroundStyle(GCTheme.muted)
                    Button("Vollständig aktualisieren") { Task { await model.refresh() } }.buttonStyle(.borderedProminent)
                })
                if model.devices.isEmpty {
                    GCPanel(content: Text("Noch keine Geräte. Unter System zuerst die FRITZ!Box verbinden oder unter Bluetooth Mars-Hydro-Geräte suchen.").foregroundStyle(GCTheme.muted))
                }
            }.padding()
        }.navigationBarHidden(true).refreshable { await model.refresh() }
    }
}

struct DevicesView: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        List {
            ForEach(model.devices) { device in
                Section {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack { Circle().fill(device.online ? GCTheme.green : GCTheme.danger).frame(width: 9, height: 9); Text(device.name).font(.headline.monospaced()); Spacer(); Text(device.provider.rawValue).font(.caption2).foregroundStyle(GCTheme.cyan) }
                        HStack { value("Leistung", device.powerW.map { "\($0.formatted(.number.precision(.fractionLength(1)))) W" } ?? "–"); value("Energie", device.energyWh.map { "\(($0 / 1000).formatted(.number.precision(.fractionLength(3)))) kWh" } ?? "–"); value("Kosten", device.energyWh.map { (($0 / 1000) * model.state.electricityPricePerKWh).formatted(.currency(code: "EUR")) } ?? "–") }
                        if device.writable, device.isOn != nil { Button(device.isOn == true ? "Ausschalten" : "Einschalten") { Task { await model.toggle(device) } }.buttonStyle(.borderedProminent).tint(device.isOn == true ? GCTheme.danger : GCTheme.green) }
                    }.padding(.vertical, 6)
                }
            }
        }.scrollContentBackground(.hidden).navigationTitle("Geräte").refreshable { await model.refresh() }
    }
    private func value(_ title: String, _ value: String) -> some View { VStack(alignment: .leading) { Text(title).font(.caption2).foregroundStyle(GCTheme.muted); Text(value).font(.caption.monospaced()).foregroundStyle(GCTheme.cyan) }.frame(maxWidth: .infinity, alignment: .leading) }
}

struct HistoryView: View {
    @EnvironmentObject var model: AppModel
    @State private var period: HistoryPeriod = .day
    var samples: [EnergySample] { model.samples(period: period) }
    var body: some View {
        ScrollView {
            VStack(spacing: 14) {
                GCTitle(title: "Verbrauch & Kosten")
                Picker("Zeitraum", selection: $period) { ForEach(HistoryPeriod.allCases) { Text($0.rawValue).tag($0) } }.pickerStyle(.segmented)
                GCPanel(content: Chart(samples) { sample in
                    LineMark(x: .value("Zeit", sample.timestamp), y: .value("W", sample.powerW)).foregroundStyle(GCTheme.cyan)
                    AreaMark(x: .value("Zeit", sample.timestamp), y: .value("W", sample.powerW)).foregroundStyle(LinearGradient(colors: [GCTheme.cyan.opacity(0.3), .clear], startPoint: .top, endPoint: .bottom))
                }.frame(height: 230).chartYAxisLabel("W"))
                HStack { GCMetric(title: "Aktuell", value: "\(model.currentPowerW.formatted(.number.precision(.fractionLength(1)))) W", tint: GCTheme.cyan); GCMetric(title: "Kosten gesamt", value: model.totalCost.formatted(.currency(code: "EUR")), tint: GCTheme.green) }
                Text("Die Kosten basieren auf der Gesamtenergie und bleiben auch bei ausgeschalteter Steckdose erhalten.").font(.caption).foregroundStyle(GCTheme.muted)
            }.padding()
        }.navigationBarHidden(true)
    }
}

struct BluetoothView: View {
    @ObservedObject var bluetooth: BluetoothManager
    var body: some View {
        List {
            Section { HStack { Text(bluetooth.state); Spacer(); Button(bluetooth.scanning ? "Stoppen" : "8 s suchen") { bluetooth.scanning ? bluetooth.stop() : bluetooth.scan() } } }
            Section("Gefundene Geräte") {
                ForEach(bluetooth.devices) { item in
                    VStack(alignment: .leading, spacing: 5) { HStack { Text(item.name).font(.headline); if item.isMarsHydro { Text("MARS HYDRO").font(.caption2).foregroundStyle(GCTheme.green) }; Spacer(); Text("\(item.rssi) dBm").font(.caption.monospaced()) }; Text(item.id.uuidString).font(.caption2.monospaced()).foregroundStyle(GCTheme.muted) }
                }
            }
            Section { Text("DF100M/MZ_MZF002 wird als Diagnosekandidat erkannt. Schreibbefehle bleiben gesperrt, bis das Protokoll an realer Hardware sicher validiert ist.").font(.caption).foregroundStyle(GCTheme.muted) }
        }.scrollContentBackground(.hidden).navigationTitle("Bluetooth")
    }
}

struct SettingsView: View {
    @EnvironmentObject var model: AppModel
    @State private var password = ""
    var body: some View {
        Form {
            Section("FRITZ!Box lokal") {
                TextField("Adresse", text: $model.state.fritzHost).textInputAutocapitalization(.never).autocorrectionDisabled()
                TextField("FRITZ!-Benutzer", text: $model.state.fritzUsername).textInputAutocapitalization(.never).autocorrectionDisabled()
                SecureField(model.hasFritzPassword ? "Neues Passwort (optional)" : "Passwort", text: $password)
                Button("Anmeldung prüfen und Geräte importieren") { let value = password; Task { await model.testAndImportFritz(password: value); password = "" } }.disabled(password.isEmpty || model.state.fritzUsername.isEmpty)
                if model.hasFritzPassword { Button("Gespeicherte Anmeldung löschen", role: .destructive) { model.deleteFritzLogin() } }
            }
            Section("Stromkosten") {
                HStack { Text("Preis je kWh"); Spacer(); TextField("0,35", value: $model.state.electricityPricePerKWh, format: .number).keyboardType(.decimalPad).multilineTextAlignment(.trailing); Text("€") }
            }
            Section("Tapo") { Text("Der aktuelle iOS-Testbuild enthält noch keinen validierten nativen Tapo/KLAP-Transport. Es werden keine Cloud-Funktionen vorgetäuscht.").font(.caption).foregroundStyle(GCTheme.muted) }
            Section("Betriebsgrenze iOS") { Text("iOS beendet beliebige Dauerprozesse im Hintergrund. Zeitpläne und Schutzautomationen laufen deshalb nur zuverlässig, solange die App aktiv ist. Für unbeaufsichtigten 24/7-Betrieb bleibt der Raspberry Pi die freigegebene Instanz.").font(.caption).foregroundStyle(GCTheme.muted) }
            Section { Button("Einstellungen speichern") { model.save(); model.message = "Einstellungen gespeichert." } }
        }.scrollContentBackground(.hidden).navigationTitle("System")
    }
}
