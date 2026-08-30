import AppKit
import SwiftUI

struct WindowBehaviorBridge: NSViewRepresentable {
    func makeNSView(context: Context) -> WindowBehaviorView {
        WindowBehaviorView()
    }

    func updateNSView(_ nsView: WindowBehaviorView, context: Context) {}
}

final class WindowBehaviorView: NSView {
    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        window?.isMovableByWindowBackground = true
    }
}
