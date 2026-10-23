import AppKit
import Darwin
import Foundation

@main
struct NativeLifecycleRegression {
    @MainActor
    static func main() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data("server lifecycle fixture".utf8).write(to: root.appendingPathComponent("index.html"))
        defer { try? FileManager.default.removeItem(at: root) }

        let center = NotificationCenter()
        let control = LocalDashboardServer()
        let controlIdentity = start(control, root: root)
        defer { control.stop() }

        let owned = LocalDashboardServer()
        let ownedIdentity = start(owned, root: root)
        var model: AtlasAppModel? = AtlasAppModel(server: owned, notificationCenter: center)
        let modelProbe = WeakProbe(model)
        withExtendedLifetime(model) {
            center.post(name: NSApplication.willTerminateNotification, object: nil)
            precondition(modelProbe.value != nil, "Quit cleanup must run while the model is still retained")
            waitForExit(ownedIdentity)
            precondition(owned.process == nil && owned.port == nil)
            precondition(controlIdentity.process.isRunning && canConnect(controlIdentity.port),
                         "Quit cleanup touched an unrelated server")
            center.post(name: NSApplication.willTerminateNotification, object: nil)
        }
        model = nil
        precondition(modelProbe.value == nil, "Termination observer retained the model")

        // A fresh model owns a fresh service after the previous one stopped.
        let reopened = LocalDashboardServer()
        let reopenedIdentity = start(reopened, root: root)
        var reopenedModel: AtlasAppModel? = AtlasAppModel(server: reopened, notificationCenter: center)
        withExtendedLifetime(reopenedModel) {
            center.post(name: NSApplication.willTerminateNotification, object: nil)
            waitForExit(reopenedIdentity)
        }
        reopenedModel = nil

        // Removing the observer on deinit must release its captured server too.
        var releasedServer: LocalDashboardServer? = LocalDashboardServer()
        let releasedIdentity = start(releasedServer!, root: root)
        let serverProbe = WeakProbe(releasedServer)
        var releasedModel: AtlasAppModel? = AtlasAppModel(server: releasedServer!, notificationCenter: center)
        let releasedModelProbe = WeakProbe(releasedModel)
        releasedServer = nil
        withExtendedLifetime(releasedModel) {}
        releasedModel = nil
        precondition(releasedModelProbe.value == nil && serverProbe.value == nil,
                     "Deinit did not remove the observer and release its server")
        waitForExit(releasedIdentity)
        precondition(controlIdentity.process.isRunning && canConnect(controlIdentity.port))
        print("Quit cleanup closed the owned process/socket; unrelated server, reopen and observer lifetime checks passed.")
    }

    private static func start(_ server: LocalDashboardServer, root: URL) -> (process: Process, port: Int) {
        var startupError: Error?
        server.start(root: root) { result in
            if case .failure(let error) = result { startupError = error }
        }
        let deadline = Date().addingTimeInterval(10)
        while server.url == nil && startupError == nil && Date() < deadline {
            RunLoop.current.run(until: Date().addingTimeInterval(0.01))
        }
        if let startupError { fatalError("Startup failed: \(startupError)") }
        guard let process = server.process, let port = server.port else { fatalError("Startup timed out") }
        precondition(process.isRunning && canConnect(port))
        return (process, port)
    }

    private static func waitForExit(_ identity: (process: Process, port: Int)) {
        let deadline = Date().addingTimeInterval(5)
        while (identity.process.isRunning || canConnect(identity.port)) && Date() < deadline {
            RunLoop.current.run(until: Date().addingTimeInterval(0.01))
        }
        precondition(!identity.process.isRunning, "Owned child process survived cleanup")
        precondition(!canConnect(identity.port), "Owned listening socket survived cleanup")
    }

    private static func canConnect(_ port: Int) -> Bool {
        let descriptor = socket(AF_INET, SOCK_STREAM, 0)
        precondition(descriptor >= 0)
        defer { close(descriptor) }
        var address = sockaddr_in()
        address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = in_port_t(port).bigEndian
        address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))
        return withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                connect(descriptor, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) == 0
            }
        }
    }
}

private final class WeakProbe<Value: AnyObject> {
    weak var value: Value?
    init(_ value: Value?) { self.value = value }
}
