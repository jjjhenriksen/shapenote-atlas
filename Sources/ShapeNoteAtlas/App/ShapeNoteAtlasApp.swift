import AppKit
import SwiftUI

@main
struct ShapeNoteAtlasApp: App {
    @StateObject private var model = AtlasAppModel()

    init() {
        NSApplication.shared.setActivationPolicy(.regular)
    }

    var body: some Scene {
        WindowGroup("The Shape-Note Atlas") {
            AtlasContentView(model: model)
                .ignoresSafeArea(.container, edges: .top)
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
