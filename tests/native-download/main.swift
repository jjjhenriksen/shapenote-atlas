import AppKit
import Foundation
import WebKit

func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fatalError(message) }
}

@MainActor
func waitFor(_ message: String, until condition: () -> Bool) {
    let deadline = Date().addingTimeInterval(10)
    while !condition() && Date() < deadline {
        RunLoop.current.run(until: Date().addingTimeInterval(0.01))
    }
    require(condition(), message)
}

@MainActor
func evaluate(_ script: String, in webView: WKWebView) -> Any? {
    var completed = false
    var value: Any?
    webView.evaluateJavaScript(script) { result, error in
        require(error == nil, "JavaScript failed: \(String(describing: error))")
        value = result
        completed = true
    }
    waitFor("JavaScript did not complete") { completed }
    return value
}

@main
struct NativeDownloadRegression {
    @MainActor
    static func main() throws {
        // No window, panel, app bundle, or foreground activation is used here.
        _ = NSApplication.shared
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let existing = root.appendingPathComponent("existing.musicxml")
        let original = Data("Keep the existing score untouched.\r\n".utf8)
        try original.write(to: existing)
        let newFile = root.appendingPathComponent("new.musicxml")
        try AtlasWebViewCoordinator.validateDownloadDestination(newFile)
        for blocked in [existing, root, URL(string: "https://example.invalid/score.musicxml")!] {
            do {
                try AtlasWebViewCoordinator.validateDownloadDestination(blocked)
                fatalError("An existing or non-file destination must be rejected")
            } catch {}
        }
        let danglingLink = root.appendingPathComponent("dangling.musicxml")
        try FileManager.default.createSymbolicLink(at: danglingLink, withDestinationURL: newFile)
        do {
            try AtlasWebViewCoordinator.validateDownloadDestination(danglingLink)
            fatalError("An existing symbolic link must be rejected")
        } catch {}

        let server = Process()
        let output = Pipe()
        server.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        server.arguments = ["tests/native-download/fixture-server.py"]
        server.standardOutput = output
        try server.run()
        defer { if server.isRunning { server.terminate() } }
        let portText = String(decoding: output.fileHandleForReading.availableData, as: UTF8.self)
        guard let port = Int(portText.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            fatalError("Fixture server did not start")
        }
        let readerURL = URL(string: "http://127.0.0.1:\(port)/")!
        let coordinator = AtlasWebViewCoordinator()
        let webView = WKWebView(frame: .zero)
        webView.navigationDelegate = coordinator
        webView.uiDelegate = coordinator
        var pageFailures = [String]()
        var downloadFailures = [Error]()
        var selections = [String]()
        var destination: URL? = newFile
        coordinator.onFailure = { pageFailures.append($0) }
        coordinator.onDownloadFailure = { downloadFailures.append($0) }
        coordinator.selectDownloadDestination = { name, originatingView, completion in
            require(originatingView === webView, "The originating reader should own the save panel")
            selections.append(name)
            completion(destination)
        }
        webView.load(URLRequest(url: readerURL))
        waitFor("Fixture page did not load") { webView.url == readerURL && !webView.isLoading }
        let payload = Data((0..<65_536).map { UInt8(truncatingIfNeeded: $0) })

        _ = evaluate("document.getElementById('action').click()", in: webView)
        waitFor("The download attribute did not save unchanged bytes") { (try? Data(contentsOf: newFile)) == payload }
        require(selections == ["fixture.musicxml"], "The link's download filename should be preserved")

        let responseFile = root.appendingPathComponent("response.bin")
        destination = responseFile
        _ = evaluate("document.getElementById('response').click()", in: webView)
        waitFor("The response policy did not download unsupported MIME bytes") { (try? Data(contentsOf: responseFile)) == payload }

        destination = nil
        _ = evaluate("document.getElementById('action').click()", in: webView)
        waitFor("The cancelled download did not reach destination selection") { selections.count == 3 }

        destination = existing
        _ = evaluate("document.getElementById('action').click()", in: webView)
        waitFor("The existing destination was not rejected") { downloadFailures.count == 1 }
        require((try? Data(contentsOf: existing)) == original, "An existing score must remain unchanged")

        destination = root.appendingPathComponent("broken.bin")
        _ = evaluate("document.getElementById('broken').click()", in: webView)
        waitFor("A truncated transfer did not report a download failure") { downloadFailures.count == 2 }
        require(pageFailures.isEmpty, "Download success, cancellation, and failure must preserve the reader")
        require(webView.url == readerURL, "A download must not replace the reader URL")
        require(evaluate("document.title", in: webView) as? String == "Native download fixture",
                "The reader must remain usable after a failed download")

        for expected in [NSError(domain: NSURLErrorDomain, code: NSURLErrorCancelled),
                         NSError(domain: "WebKitErrorDomain", code: 102)] {
            coordinator.webView(webView, didFailProvisionalNavigation: nil, withError: expected)
        }
        require(pageFailures.isEmpty, "Expected navigation cancellation must not report a page failure")
        for genuine in [NSError(domain: NSURLErrorDomain, code: NSURLErrorCannotConnectToHost),
                        NSError(domain: WKErrorDomain, code: 102),
                        NSError(domain: "WebKitErrorDomain", code: 101)] {
            coordinator.webView(webView, didFailProvisionalNavigation: nil, withError: genuine)
        }
        require(pageFailures.count == 3, "Genuine page errors must still reach the recovery UI")
        print("Native WebKit download checks passed: action, response, unchanged bytes, cancel, no-clobber, transfer failure, healthy reader.")
    }
}
