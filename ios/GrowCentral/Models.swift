import Foundation

enum DeviceProvider: String, Codable, CaseIterable {
    case fritz = "FRITZ!"
    case tapo = "Tapo"
    case marsHydro = "Mars Hydro"
    case other = "Andere"
}

struct SmartDevice: Identifiable, Codable, Hashable {
    var id: String
    var name: String
    var provider: DeviceProvider
    var room: String?
    var nativeID: String?
    var model: String?
    var online = false
    var isOn: Bool?
    var powerW: Double?
    var energyWh: Double?
    var temperatureC: Double?
    var writable = false
    var lastSeen: Date?
}

struct EnergySample: Identifiable, Codable, Hashable {
    var id = UUID()
    var deviceID: String
    var timestamp: Date
    var powerW: Double
    var energyWh: Double
}

enum HistoryPeriod: String, CaseIterable, Identifiable {
    case hour = "Stunde", day = "Tag", month = "Monat", year = "Jahr"
    var id: String { rawValue }
    var seconds: TimeInterval {
        switch self { case .hour: return 3_600; case .day: return 86_400; case .month: return 2_629_800; case .year: return 31_557_600 }
    }
}

struct PersistedState: Codable {
    var devices: [SmartDevice] = []
    var samples: [EnergySample] = []
    var electricityPricePerKWh: Double = 0.35
    var fritzHost = "fritz.box"
    var fritzUsername = ""
}

