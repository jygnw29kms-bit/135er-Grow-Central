import Foundation

enum FritzError: LocalizedError {
    case invalidHost, invalidResponse, loginFailed, unsupportedChallenge, missingDevice
    var errorDescription: String? {
        switch self {
        case .invalidHost: return "Ungültige FRITZ!Box-Adresse."
        case .invalidResponse: return "Die FRITZ!Box hat unerwartet geantwortet."
        case .loginFailed: return "FRITZ!Box-Anmeldung fehlgeschlagen. Benutzer, Passwort und Rechte prüfen."
        case .unsupportedChallenge: return "Diese FRITZ!OS-Anmeldemethode wird noch nicht unterstützt."
        case .missingDevice: return "Gerät wurde von der FRITZ!Box nicht gefunden."
        }
    }
}

actor FritzAHAClient {
    private let host: String
    private let username: String
    private let password: String
    private var sid: String?
    private let session: URLSession

    init(host: String, username: String, password: String) {
        self.host = host.trimmingCharacters(in: .whitespacesAndNewlines)
        self.username = username
        self.password = password
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 8
        config.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        self.session = URLSession(configuration: config)
    }

    private var baseURL: URL? {
        let raw = host.contains("://") ? host : "http://\(host)"
        return URL(string: raw)
    }

    private func request(_ path: String, query: [URLQueryItem]) async throws -> Data {
        guard let baseURL, var parts = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false) else { throw FritzError.invalidHost }
        parts.queryItems = query
        guard let url = parts.url else { throw FritzError.invalidHost }
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else { throw FritzError.invalidResponse }
        return data
    }

    func login() async throws {
        let initial = try await request("login_sid.lua", query: [URLQueryItem(name: "version", value: "2")])
        let parser = FritzLoginParser(data: initial)
        guard let challenge = parser.challenge else { throw FritzError.invalidResponse }
        let response = try challengeResponse(challenge)
        let result = try await request("login_sid.lua", query: [
            URLQueryItem(name: "version", value: "2"), URLQueryItem(name: "username", value: username), URLQueryItem(name: "response", value: response)
        ])
        let login = FritzLoginParser(data: result)
        guard let newSID = login.sid, newSID != "0000000000000000" else { throw FritzError.loginFailed }
        sid = newSID
    }

    private func challengeResponse(_ challenge: String) throws -> String {
        guard challenge.hasPrefix("2$") else { throw FritzError.unsupportedChallenge }
        let parts = challenge.split(separator: "$", omittingEmptySubsequences: false)
        guard parts.count == 5, let iteration1 = Int(parts[1]), let salt1 = Data(hex: String(parts[2])),
              let iteration2 = Int(parts[3]), let salt2 = Data(hex: String(parts[4])) else { throw FritzError.invalidResponse }
        let hash1 = PBKDF2.sha256(password: Data(password.utf8), salt: salt1, iterations: iteration1)
        let hash2 = PBKDF2.sha256(password: hash1, salt: salt2, iterations: iteration2)
        return "\(challenge)$\(hash2.hexString)"
    }

    func devices() async throws -> [SmartDevice] {
        if sid == nil { try await login() }
        guard let sid else { throw FritzError.loginFailed }
        let data = try await request("webservices/homeautoswitch.lua", query: [URLQueryItem(name: "sid", value: sid), URLQueryItem(name: "switchcmd", value: "getdevicelistinfos")])
        return FritzDeviceParser(data: data).devices
    }

    func setSwitch(ain: String, on: Bool) async throws {
        if sid == nil { try await login() }
        guard let sid else { throw FritzError.loginFailed }
        _ = try await request("webservices/homeautoswitch.lua", query: [
            URLQueryItem(name: "sid", value: sid), URLQueryItem(name: "ain", value: ain),
            URLQueryItem(name: "switchcmd", value: on ? "setswitchon" : "setswitchoff")
        ])
    }
}

private final class FritzLoginParser: NSObject, XMLParserDelegate {
    var challenge: String?; var sid: String?
    private var active = ""; private var text = ""
    init(data: Data) { super.init(); let parser = XMLParser(data: data); parser.delegate = self; parser.parse() }
    func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?, qualifiedName qName: String?, attributes attributeDict: [String : String] = [:]) { active = elementName; text = "" }
    func parser(_ parser: XMLParser, foundCharacters string: String) { text += string }
    func parser(_ parser: XMLParser, didEndElement elementName: String, namespaceURI: String?, qualifiedName qName: String?) {
        if elementName == "Challenge" { challenge = text.trimmingCharacters(in: .whitespacesAndNewlines) }
        if elementName == "SID" { sid = text.trimmingCharacters(in: .whitespacesAndNewlines) }
        active = ""
    }
}

private final class FritzDeviceParser: NSObject, XMLParserDelegate {
    var devices: [SmartDevice] = []
    private var current: SmartDevice?; private var active = ""; private var text = ""
    init(data: Data) { super.init(); let parser = XMLParser(data: data); parser.delegate = self; parser.parse() }
    func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?, qualifiedName qName: String?, attributes attributes: [String : String] = [:]) {
        active = elementName; text = ""
        if elementName == "device" {
            let ain = (attributes["identifier"] ?? "").trimmingCharacters(in: .whitespaces)
            current = SmartDevice(id: "fritz-\(ain)", name: "FRITZ! Smart Home", provider: .fritz, nativeID: ain,
                                  model: attributes["productname"], online: false, writable: true)
        }
    }
    func parser(_ parser: XMLParser, foundCharacters string: String) { text += string }
    func parser(_ parser: XMLParser, didEndElement elementName: String, namespaceURI: String?, qualifiedName qName: String?) {
        let value = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard var item = current else { return }
        switch elementName {
        case "name": if !value.isEmpty { item.name = value }
        case "present": item.online = value == "1"; item.lastSeen = item.online ? Date() : nil
        case "state": item.isOn = value == "1"
        case "power": item.powerW = Double(value).map { $0 / 1000 }
        case "energy": item.energyWh = Double(value)
        case "celsius": item.temperatureC = Double(value).map { $0 / 10 }
        case "device": devices.append(item); current = nil; return
        default: break
        }
        current = item; active = ""
    }
}

