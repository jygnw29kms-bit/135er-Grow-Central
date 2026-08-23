import XCTest
@testable import GrowCentral

@MainActor
final class GrowCentralTests: XCTestCase {
    func testLocalAddressGetsHTTPWhenSchemeIsMissing() {
        let settings = ConnectionSettings(defaults: UserDefaults(suiteName: UUID().uuidString)!)
        XCTAssertEqual(settings.normalizedURL("135er-Grow-Central.local", requireHTTPS: false)?.absoluteString,
                       "http://135er-Grow-Central.local/")
    }

    func testRemoteServerRequiresHTTPS() {
        let settings = ConnectionSettings(defaults: UserDefaults(suiteName: UUID().uuidString)!)
        XCTAssertNil(settings.normalizedURL("http://example.test", requireHTTPS: true))
        XCTAssertEqual(settings.normalizedURL("https://example.test", requireHTTPS: true)?.absoluteString,
                       "https://example.test/")
    }
}
