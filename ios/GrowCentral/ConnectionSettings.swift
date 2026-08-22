import Foundation
import Combine

@MainActor
final class ConnectionSettings: ObservableObject {
    enum Mode: String, CaseIterable, Identifiable {
        case local
        case server
        var id: String { rawValue }
        var label: String { self == .local ? "Heimnetz" : "Server · überall" }
    }

    @Published var localAddress: String { didSet { defaults.set(localAddress, forKey: Keys.localAddress) } }
    @Published var serverAddress: String { didSet { defaults.set(serverAddress, forKey: Keys.serverAddress) } }
    @Published var mode: Mode { didSet { defaults.set(mode.rawValue, forKey: Keys.mode) } }

    private let defaults: UserDefaults
    private enum Keys {
        static let localAddress = "connection.localAddress"
        static let serverAddress = "connection.serverAddress"
        static let mode = "connection.mode"
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        localAddress = defaults.string(forKey: Keys.localAddress) ?? "http://135er-Grow-Central.local/"
        serverAddress = defaults.string(forKey: Keys.serverAddress) ?? ""
        mode = Mode(rawValue: defaults.string(forKey: Keys.mode) ?? "local") ?? .local
    }

    var activeURL: URL? { normalizedURL(mode == .local ? localAddress : serverAddress, requireHTTPS: mode == .server) }
    var serverConfigured: Bool { normalizedURL(serverAddress, requireHTTPS: true) != nil }

    func normalizedURL(_ value: String, requireHTTPS: Bool) -> URL? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let prepared = trimmed.contains("://") ? trimmed : "\(requireHTTPS ? "https" : "http")://\(trimmed)"
        guard var parts = URLComponents(string: prepared), let host = parts.host, !host.isEmpty else { return nil }
        if requireHTTPS && parts.scheme?.lowercased() != "https" { return nil }
        if parts.path.isEmpty { parts.path = "/" }
        return parts.url
    }
}
