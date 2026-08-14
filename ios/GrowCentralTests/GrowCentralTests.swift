import XCTest
@testable import GrowCentral

final class GrowCentralTests: XCTestCase {
    func testPBKDF2Vector() {
        let result = PBKDF2.sha256(password: Data("password".utf8), salt: Data("salt".utf8), iterations: 1, length: 32)
        XCTAssertEqual(result.hexString, "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b")
    }
    func testPeriodsAreOrderedBySize() {
        XCTAssertLessThan(HistoryPeriod.hour.seconds, HistoryPeriod.day.seconds)
        XCTAssertLessThan(HistoryPeriod.day.seconds, HistoryPeriod.month.seconds)
        XCTAssertLessThan(HistoryPeriod.month.seconds, HistoryPeriod.year.seconds)
    }
}

