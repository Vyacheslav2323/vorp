import Foundation
import Combine
import AVFoundation

final class RecordingManager: ObservableObject {
    @Published var status = "Idle"
    @Published var transcript = ""
	private var timer: Timer?
    private var engine = AVAudioEngine()
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    private var subs = Set<AnyCancellable>()
    private var conv: AVAudioConverter?
    private var pingTimer: Timer?

	init() {
		startTimer()
	}

	func prepareStart() {
		setStatus("Recording…")
		setStop(false)
        _ = connect()
        _ = configureSession()
        _ = startMic()
	}

	func requestStop() {
		setStop(true)
        stopMic()
        close()
	}

	private func setStatus(_ s: String) {
        DispatchQueue.main.async { self.status = s }
		let d = UserDefaults(suiteName: Constants.appGroupId)
		d?.set(s, forKey: Constants.statusKey)
		d?.synchronize()
		_ = Logger.write("status:\t" + s)
	}

	private func setStop(_ v: Bool) {
		let d = UserDefaults(suiteName: Constants.appGroupId)
		d?.set(v, forKey: Constants.stopFlagKey)
		d?.synchronize()
		_ = Logger.write("stop:\t" + String(v))
	}

	private func startTimer() {
		timer?.invalidate()
		timer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
			self?.poll()
		}
	}

	private func poll() {
		let d = UserDefaults(suiteName: Constants.appGroupId)
		guard let p = d?.string(forKey: Constants.savedPathKey), !p.isEmpty else { return }
		setStatus("Saved to Documents")
		d?.removeObject(forKey: Constants.savedPathKey)
	}

    private func connect() -> Bool {
        let u = URL(string: Constants.wsURL)
        guard let url = u else { return false }
        let s = URLSession(configuration: .default)
        session = s
        let t = s.webSocketTask(with: url)
        socket = t
        t.resume()
        receive()
        let hello: [String: Any] = ["session_id": UUID().uuidString, "codec": "pcm_s16le", "rate_hz": 16000, "lang": "ko-KR"]
        let data = try? JSONSerialization.data(withJSONObject: hello)
        let str = String(data: data ?? Data(), encoding: .utf8) ?? "{}"
        t.send(.string(str)) { _ in }
        startPing()
        return true
    }

    private func close() {
        pingTimer?.invalidate()
        socket?.cancel(with: .goingAway, reason: nil)
        socket = nil
        session = nil
    }

    private func receive() {
        socket?.receive { [weak self] r in
            if case .success(let m) = r {
                if case .string(let s) = m { _ = self?.handleMessage(s) }
            }
            self?.receive()
        }
    }

    private func handleMessage(_ s: String) -> Bool {
        if let d = s.data(using: .utf8),
           let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
            let t = (j["type"] as? String) ?? ""
            let x = (j["text"] as? String) ?? ""
            if t == "final" && !x.isEmpty { _ = appendTranscript(x); setStatus(x); return true }
        }
        setStatus(s)
        return false
    }

    private func startMic() -> Bool {
        let i = engine.inputNode
        engine.inputNode.removeTap(onBus: 0)
        let inFmt = i.inputFormat(forBus: 0)
        guard let outFmt = micFormat() else { return false }
        conv = AVAudioConverter(from: inFmt, to: outFmt)
        i.installTap(onBus: 0, bufferSize: 1024, format: inFmt) { [weak self] buf, _ in
            guard let s = self?.socket else { return }
            guard let ob = self?.convert(buf) else { return }
            let d = self?.asS16(ob) ?? Data()
            let n = d.count
            s.send(.data(d)) { _ in }
            let rms = self?.rms(ob) ?? 0
            _ = Logger.write("send_bytes:\t" + String(n) + "\trms:\t" + String(format: "%.5f", rms))
        }
        do {
            try engine.start()
            return true
        } catch {
            return false
        }
    }

    private func micFormat() -> AVAudioFormat? {
        AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 16000, channels: 1, interleaved: true)
    }

    private func configureSession() -> Bool {
        let s = AVAudioSession.sharedInstance()
        do {
            try s.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .allowBluetooth, .allowBluetoothA2DP, .allowAirPlay])
            try s.setPreferredSampleRate(16000)
            try s.setActive(true)
            return true
        } catch {
            return false
        }
    }

    private func rms(_ b: AVAudioPCMBuffer) -> Float {
        let n = Int(b.frameLength)
        guard n > 0, let p = b.floatChannelData?[0] else { return 0 }
        var sum: Float = 0
        for i in 0..<n { let v = p[i]; sum += v*v }
        return sqrtf(sum / Float(n))
    }

    private func asS16(_ b: AVAudioPCMBuffer) -> Data {
        let n = Int(b.frameLength)
        guard n > 0, let p = b.floatChannelData?[0] else { return Data() }
        var out = Data(count: n * 2)
        out.withUnsafeMutableBytes { q in
            let dst = q.bindMemory(to: Int16.self).baseAddress!
            for i in 0..<n {
                let v = max(-1.0, min(1.0, Double(p[i])))
                dst[i] = Int16(v * 32767.0)
            }
        }
        return out
    }

    private func convert(_ b: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let f = micFormat(), let c = conv else { return nil }
        let cap = max(2048, Int(b.frameLength))
        guard let o = AVAudioPCMBuffer(pcmFormat: f, frameCapacity: AVAudioFrameCount(cap)) else { return nil }
        var e: NSError?
        c.convert(to: o, error: &e) { _, outStatus in outStatus.pointee = .haveData; return b }
        return o
    }

    private func startPing() {
        pingTimer?.invalidate()
        pingTimer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            self?.socket?.send(.string("{\"type\":\"ping\"}")) { _ in }
        }
    }

    private func stopMic() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
    }

    func resetTranscript() -> Bool {
        DispatchQueue.main.async { self.transcript = "" }
        return true
    }

    private func appendTranscript(_ s: String) -> Bool {
        let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return false }
        DispatchQueue.main.async { self.transcript = (self.transcript + " " + t).trimmingCharacters(in: .whitespacesAndNewlines) }
        _ = Logger.write("transcript:\t" + t)
        return true
    }
}


