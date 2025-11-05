import SwiftUI

@main
struct LexiParkRecorderApp: App {
	@StateObject private var manager = RecordingManager()

	var body: some Scene {
		WindowGroup {
			ContentView(manager: manager)
		}
	}
}


