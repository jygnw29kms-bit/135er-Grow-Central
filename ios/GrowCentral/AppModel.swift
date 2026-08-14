import Foundation

@MainActor
final class AppModel: ObservableObject {
    @Published var state = PersistedState()
    @Published var loading = false
    @Published var message: String?
    @Published var lastRefresh: Date?
    @Published var selectedTab = 0
    let bluetooth = BluetoothManager()
    private let persistence = Persistence()

    var devices: [SmartDevice] { state.devices }
    var onlineCount: Int { devices.filter(\.online).count }
    var currentPowerW: Double { devices.compactMap(\.powerW).reduce(0, +) }
    var totalEnergyWh: Double { devices.compactMap(\.energyWh).reduce(0, +) }
    var totalCost: Double { totalEnergyWh / 1000 * state.electricityPricePerKWh }

    func load() async { state = await persistence.load() }
    func save() { let snapshot = state; Task { await persistence.save(snapshot) } }

    func saveFritzPassword(_ value: String) throws { try KeychainStore.set(value, account: "fritz-password") }
    var hasFritzPassword: Bool { KeychainStore.get("fritz-password") != nil }

    func refresh() async {
        guard !loading else { return }
        guard !state.fritzUsername.isEmpty, let password = KeychainStore.get("fritz-password") else {
            lastRefresh = Date(); return
        }
        loading = true; defer { loading = false }
        do {
            let client = FritzAHAClient(host: state.fritzHost, username: state.fritzUsername, password: password)
            let fresh = try await client.devices()
            merge(fresh)
            lastRefresh = Date(); message = nil; save()
        } catch { message = error.localizedDescription }
    }

    func testAndImportFritz(password: String) async {
        loading = true; defer { loading = false }
        do {
            let client = FritzAHAClient(host: state.fritzHost, username: state.fritzUsername, password: password)
            let fresh = try await client.devices()
            try saveFritzPassword(password)
            merge(fresh); lastRefresh = Date(); message = "\(fresh.count) FRITZ!-Gerät(e) importiert."; save()
        } catch { message = error.localizedDescription }
    }

    func toggle(_ device: SmartDevice) async {
        guard device.provider == .fritz, let ain = device.nativeID, let password = KeychainStore.get("fritz-password"), let newValue = device.isOn.map({ !$0 }) else { return }
        loading = true; defer { loading = false }
        do {
            let client = FritzAHAClient(host: state.fritzHost, username: state.fritzUsername, password: password)
            try await client.setSwitch(ain: ain, on: newValue)
            await refresh()
        } catch { message = error.localizedDescription }
    }

    private func merge(_ fresh: [SmartDevice]) {
        var byID = Dictionary(uniqueKeysWithValues: state.devices.map { ($0.id, $0) })
        for var device in fresh {
            if device.energyWh == nil { device.energyWh = byID[device.id]?.energyWh }
            byID[device.id] = device
            if let power = device.powerW, let energy = device.energyWh {
                state.samples.append(EnergySample(deviceID: device.id, timestamp: Date(), powerW: power, energyWh: energy))
            }
        }
        state.devices = byID.values.sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
        let cutoff = Date().addingTimeInterval(-31_557_600)
        state.samples.removeAll { $0.timestamp < cutoff }
    }

    func samples(period: HistoryPeriod) -> [EnergySample] {
        let cutoff = Date().addingTimeInterval(-period.seconds)
        return state.samples.filter { $0.timestamp >= cutoff }.sorted { $0.timestamp < $1.timestamp }
    }

    func deleteFritzLogin() { KeychainStore.delete("fritz-password"); message = "FRITZ!-Anmeldung gelöscht." }
}

