import Foundation

func appDocumentsURL() -> URL {
    FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
}

func moveRecording(path: String) -> String? {
    let src = URL(fileURLWithPath: path)
    let dst = appDocumentsURL().appendingPathComponent(src.lastPathComponent)
    do {
        if FileManager.default.fileExists(atPath: dst.path) {
            try FileManager.default.removeItem(at: dst)
        }
        try FileManager.default.moveItem(at: src, to: dst)
        _ = Logger.write("moved:\t\(path) -> \(dst.path)")
        return dst.path
    } catch {
        _ = Logger.write("move_error:\t\(error.localizedDescription)")
        return nil
    }
}

func listRecordings() -> [String] {
    let u = appDocumentsURL()
    let items = (try? FileManager.default.contentsOfDirectory(atPath: u.path)) ?? []
    let xs = items.filter { $0.hasSuffix(".m4a") }.sorted()
    _ = Logger.write("docs:\t\(xs)")
    return xs
}


