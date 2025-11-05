import Foundation

enum Logger {
    static func url() -> URL? {
        FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: Constants.appGroupId)?
            .appendingPathComponent("log.txt")
    }

    @discardableResult
    static func write(_ text: String) -> Bool {
        guard let u = url() else { return false }
        _ = rotate(u)
        let line = "[" + now() + "] " + text + "\n"
        let data = line.data(using: .utf8) ?? Data()

        if FileManager.default.fileExists(atPath: u.path) {
            return append(u, data)
        } else {
            return create(u, data)
        }
    }

    private static func append(_ url: URL, _ data: Data) -> Bool {
        do {
            let handle = try FileHandle(forWritingTo: url)
            defer { try? handle.close() }
            try handle.seekToEnd()
            try handle.write(contentsOf: data)
            return true
        } catch {
            return false
        }
    }

    private static func create(_ url: URL, _ data: Data) -> Bool {
        do {
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try data.write(to: url, options: .atomic)
            return true
        } catch {
            return false
        }
    }

    private static func now() -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.string(from: Date())
    }

    private static func rotate(_ url: URL) -> Bool {
        let maxBytes = 512 * 1024
        guard let a = try? FileManager.default.attributesOfItem(atPath: url.path),
              let size = a[.size] as? NSNumber,
              size.intValue > maxBytes else { return true }
        let bak = url.appendingPathExtension("1")
        _ = try? FileManager.default.removeItem(at: bak)
        do {
            try FileManager.default.moveItem(at: url, to: bak)
            return true
        } catch {
            return false
        }
    }
}
