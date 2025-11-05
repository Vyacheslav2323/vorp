import ReplayKit
import AVFoundation

final class AudioWriter {
    private let writer: AVAssetWriter
    private let audioInput: AVAssetWriterInput
    private var started = false

    init?(url: URL) {
        guard let w = try? AVAssetWriter(outputURL: url, fileType: .m4a) else { return nil }
        writer = w
        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatMPEG4AAC,
            AVNumberOfChannelsKey: 2,
            AVSampleRateKey: 44100,
            AVEncoderBitRateKey: 128_000
        ]
        let input = AVAssetWriterInput(mediaType: .audio, outputSettings: settings)
        input.expectsMediaDataInRealTime = true
        guard writer.canAdd(input) else { return nil }
        writer.add(input)
        audioInput = input
    }
    private var gotAnySamples = false
    
    func append(_ sb: CMSampleBuffer) -> Bool {
        if !started {
            started = true
            let start = CMSampleBufferGetPresentationTimeStamp(sb)
            writer.startWriting()
            writer.startSession(atSourceTime: start)
        }
        guard audioInput.isReadyForMoreMediaData else { return false }
        let ok = audioInput.append(sb)
        if ok {
            gotAnySamples = true
        } else {
            _ = Logger.write("append_failed status=\(writer.status.rawValue) err=\(writer.error?.localizedDescription ?? "")")
        }
        return ok
    }

    func finish(_ completion: @escaping (Bool) -> Void) {
        if !gotAnySamples {
                    // nothing recorded -> report false
                    completion(false)
                    return
                }
        audioInput.markAsFinished()
        writer.finishWriting {
            let ok = self.writer.status == .completed
            if !ok { _ = Logger.write("finish_error status=\(self.writer.status.rawValue) err=\(self.writer.error?.localizedDescription ?? "")") }
            completion(ok)
        }
    }
}


final class SampleHandler: RPBroadcastSampleHandler {
    private var writer: AudioWriter?
    private var endWork: DispatchWorkItem?
    private var stopped = false
    private var selectedAudioType: RPSampleBufferType?
    private var endedBySystem = false
    private var currentOutURL: URL?

    private func containerURL() -> URL {
        let fm = FileManager.default
        let groupID = Constants.appGroupId
        let base = fm.containerURL(forSecurityApplicationGroupIdentifier: groupID)
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
        try? fm.createDirectory(at: base, withIntermediateDirectories: true)
        _ = Logger.write("AppGroup ID: \(groupID)")
        if FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: groupID) == nil {
            _ = Logger.write("⚠️ Failed to access AppGroup container")
        }
        return base
    }

    private var outURL: URL {
        let tmp = URL(fileURLWithPath: NSTemporaryDirectory())
        let u = tmp.appendingPathComponent("audio_\(Int(Date().timeIntervalSince1970)).m4a")
        _ = Logger.write("Writing temporarily to: \(u.path)")
        return u
    }

    override func broadcastStarted(withSetupInfo setupInfo: [String : NSObject]?) {
        stopped = false
        _ = Logger.write("broadcastStarted (audio-only)")
        scheduleStop()
    }

    override func processSampleBuffer(_ sb: CMSampleBuffer, with type: RPSampleBufferType) {
        if shouldStop() { stop("flagged"); return }

        switch type {
        case .audioApp, .audioMic:
            if selectedAudioType == nil {
                selectedAudioType = (type == .audioMic) ? .audioMic : .audioApp
                _ = Logger.write("selected_audio_type: \(selectedAudioType == .audioMic ? "mic" : "app")")
            }
            guard type == selectedAudioType else { return }
            if writer == nil {
                let u = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("audio_\(Int(Date().timeIntervalSince1970)).m4a")
                _ = Logger.write("Writing temporarily to: \(u.path)")
                _ = Logger.write("Creating AudioWriter at: \(u.path)")
                writer = AudioWriter(url: u)
                currentOutURL = u
                if writer == nil { _ = Logger.write("create_writer_failed") }
            }
            guard CMSampleBufferDataIsReady(sb) else { _ = Logger.write("buffer_not_ready"); return }
            let kind = type == .audioApp ? "audioApp" : "audioMic"
            if writer?.append(sb) == true {
                _ = Logger.write("append_ok: \(kind)")
            } else {
                _ = Logger.write("append_drop: \(kind)")
            }
        case .video:
            // ignore video entirely
            break
        @unknown default:
            break
        }
    }

    override func broadcastFinished() {
        _ = Logger.write("broadcastFinished")
        endedBySystem = true
        finishWriter()
    }

    private func scheduleStop() {
        endWork?.cancel()
        let w = DispatchWorkItem { self.stop("auto") }
        endWork = w
        DispatchQueue.main.asyncAfter(deadline: .now() + 60, execute: w) // shorten for testing if you want
    }

    private func shouldStop() -> Bool {
        if stopped { return true }
        let d = UserDefaults(suiteName: Constants.appGroupId)
        return d?.bool(forKey: Constants.stopFlagKey) == true
    }

    private func stop(_ reason: String) {
        guard !stopped else { return }
        stopped = true
        endWork?.cancel()
        _ = Logger.write("stopping: \(reason)")
        finishWriter()
    }

    private func finishWriter() {
        guard let w = writer else { complete(nil); return }
        w.finish { ok in
            let path = self.currentOutURL?.path ?? "nil"
            _ = Logger.write("finish result: \(ok ? "OK" : "NO FILE") at \(path)")
            self.complete(ok ? self.currentOutURL : nil)
        }
    }

    private func complete(_ url: URL?) {
        guard let u = url else {
            if !endedBySystem { finishBroadcastWithError(NSError(domain: "LexiPark", code: 0)) }
            endedBySystem = false
            return
        }
        let fm = FileManager.default
        let group = containerURL()
        let dest = group.appendingPathComponent(u.lastPathComponent)
        _ = try? fm.removeItem(at: dest)
        do {
            try fm.copyItem(at: u, to: dest)
            _ = Logger.write("Copied to AppGroup: \(dest.path)")
            let d = UserDefaults(suiteName: Constants.appGroupId)
            d?.set(dest.path, forKey: Constants.savedPathKey)
            d?.synchronize()
        } catch {
            _ = Logger.write("copy_error: \(error.localizedDescription)")
        }
        if !endedBySystem { finishBroadcastWithError(NSError(domain: "LexiPark", code: 0)) }
        endedBySystem = false
    }
}


