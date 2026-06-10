import CryptoKit
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

func decodeHex(_ value: String) -> Data? {
    guard value.count % 2 == 0 else {
        return nil
    }
    var result = Data()
    var index = value.startIndex
    while index < value.endIndex {
        let next = value.index(index, offsetBy: 2)
        guard let byte = UInt8(value[index..<next], radix: 16) else {
            return nil
        }
        result.append(byte)
        index = next
    }
    return result
}

guard CommandLine.arguments.count == 4 else {
    fail("usage: verifier PUBLIC_KEY_HEX DATA SIGNATURE")
}

guard
    let publicKeyData = decodeHex(CommandLine.arguments[1]),
    publicKeyData.count == 32
else {
    fail("release public key is invalid")
}

let dataURL = URL(fileURLWithPath: CommandLine.arguments[2])
let signatureURL = URL(fileURLWithPath: CommandLine.arguments[3])
guard
    let payload = try? Data(contentsOf: dataURL),
    let signature = try? Data(contentsOf: signatureURL),
    signature.count == 64
else {
    fail("release signature input is invalid")
}

do {
    let publicKey = try Curve25519.Signing.PublicKey(
        rawRepresentation: publicKeyData
    )
    guard publicKey.isValidSignature(signature, for: payload) else {
        fail("release manifest signature is invalid")
    }
} catch {
    fail("release public key could not be loaded")
}
