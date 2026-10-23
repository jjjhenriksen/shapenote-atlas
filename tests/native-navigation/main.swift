import AppKit
import Foundation
import WebKit

func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fatalError(message) }
}

@main
struct NativeNavigationRegression {
    @MainActor
    static func main() {
        _ = NSApplication.shared
        let model = AtlasAppModel()
        model.url = URL(string: "http://127.0.0.1:12345/")!
        model.pageLoadFailed("Synthetic connection failure")
        require(model.url == nil, "A failed page must leave the reader state")
        require(model.errorMessage?.contains("Synthetic connection failure") == true,
                "The recovery view needs the navigation error")

        let coordinator = AtlasWebViewCoordinator()
        let webView = WKWebView(frame: .zero)
        var failures = [String]()
        coordinator.onFailure = { failures.append($0) }
        let cancelled = NSError(domain: NSURLErrorDomain, code: NSURLErrorCancelled)
        coordinator.webView(webView, didFail: nil, withError: cancelled)
        coordinator.webView(webView, didFailProvisionalNavigation: nil, withError: cancelled)
        require(failures.isEmpty, "Cancelled navigation must preserve the healthy reader")

        let disconnected = NSError(domain: NSURLErrorDomain, code: NSURLErrorCannotConnectToHost)
        coordinator.webView(webView, didFail: nil, withError: disconnected)
        coordinator.webView(webView, didFailProvisionalNavigation: nil, withError: disconnected)
        require(failures.count == 2, "Committed and provisional failures both need recovery")

        let unrelated = NSError(domain: "SyntheticOtherDomain", code: NSURLErrorCancelled)
        coordinator.webView(webView, didFail: nil, withError: unrelated)
        require(failures.count == 3, "Cancellation filtering must match the URL error domain")
        print("Native navigation model/coordinator checks passed")
    }
}
