import SwiftUI

struct ContentView: View {
	@ObservedObject var manager: RecordingManager
	@State private var share: URL?
	@State private var showLog = false

	var body: some View {
		VStack(spacing: 16) {
			Text(manager.status)
			Button("Start Recording", action: start)
			Button("Stop Recording", action: stop)
		ScrollView {
			Text(manager.transcript)
				.font(.system(.body, design: .default))
				.frame(maxWidth: .infinity, alignment: .leading)
		}
		.frame(maxHeight: 240)
			HStack {
				Button("View Log", action: { showLog = true })
				Button("Share Log") {
					if let u = Logger.url() { share = u }
				}
			}
		}
		.sheet(item: $share, onDismiss: { share = nil }) { u in
			ShareSheet(url: u)
		}
		.sheet(isPresented: $showLog) {
			LogView()
		}
		.padding()
	}

	private func start() {
		manager.prepareStart()
	}

	private func stop() {
		manager.requestStop()
	}
}

struct ShareSheet: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: [url], applicationActivities: nil)
    }

    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}

extension URL: Identifiable {
    public var id: String { absoluteString }
}

struct LogView: View {
    @State private var text = ""

    var body: some View {
        ScrollView { Text(text).font(.system(.footnote, design: .monospaced)).frame(maxWidth: .infinity, alignment: .leading).padding() }
            .onAppear(perform: load)
    }

    private func load() {
        if let u = Logger.url() { text = (try? String(contentsOf: u)) ?? "" }
    }
}


