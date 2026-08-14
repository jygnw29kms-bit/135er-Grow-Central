import Foundation
import CryptoKit

enum PBKDF2 {
    static func sha256(password: Data, salt: Data, iterations: Int, length: Int = 32) -> Data {
        precondition(iterations > 0 && length > 0)
        let key = SymmetricKey(data: password)
        var output = Data()
        var block: UInt32 = 1
        while output.count < length {
            var bigEndian = block.bigEndian
            let blockData = withUnsafeBytes(of: &bigEndian) { Data($0) }
            var u = Data(HMAC<SHA256>.authenticationCode(for: salt + blockData, using: key))
            var t = u
            if iterations > 1 {
                for _ in 2...iterations {
                    u = Data(HMAC<SHA256>.authenticationCode(for: u, using: key))
                    for index in t.indices { t[index] ^= u[index] }
                }
            }
            output.append(t)
            block += 1
        }
        return output.prefix(length)
    }
}

extension Data {
    var hexString: String { map { String(format: "%02x", $0) }.joined() }
    init?(hex: String) {
        guard hex.count.isMultiple(of: 2) else { return nil }
        var bytes: [UInt8] = []; bytes.reserveCapacity(hex.count / 2)
        var index = hex.startIndex
        while index < hex.endIndex {
            let next = hex.index(index, offsetBy: 2)
            guard let byte = UInt8(hex[index..<next], radix: 16) else { return nil }
            bytes.append(byte); index = next
        }
        self.init(bytes)
    }
}

