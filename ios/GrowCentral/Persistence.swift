import Foundation

actor Persistence {
    private let url: URL
    init() {
        let root = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        url = root.appendingPathComponent("grow-central.json")
    }
    func load() -> PersistedState {
        guard let data = try? Data(contentsOf: url),
              let state = try? JSONDecoder.gc.decode(PersistedState.self, from: data) else { return PersistedState() }
        return state
    }
    func save(_ state: PersistedState) {
        guard let data = try? JSONEncoder.gc.encode(state) else { return }
        try? data.write(to: url, options: [.atomic, .completeFileProtectionUnlessOpen])
    }
}

extension JSONEncoder {
    static var gc: JSONEncoder { let value = JSONEncoder(); value.dateEncodingStrategy = .iso8601; return value }
}
extension JSONDecoder {
    static var gc: JSONDecoder { let value = JSONDecoder(); value.dateDecodingStrategy = .iso8601; return value }
}

