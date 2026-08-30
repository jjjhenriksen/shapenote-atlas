import AppKit
import SwiftUI
import WebKit

final class AtlasWebViewCoordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    var onFailure: ((String) -> Void)?
    var onThemeChange: ((String, String) -> Void)?

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        onFailure?(error.localizedDescription)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        onFailure?(error.localizedDescription)
    }

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        guard let url = navigationAction.request.url else { return nil }
        NSWorkspace.shared.open(url)
        return nil
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "atlasTheme", let payload = message.body as? [String: Any],
              let bookId = payload["bookId"] as? String, let mode = payload["mode"] as? String else { return }
        onThemeChange?(bookId, mode)
    }
}

struct AtlasWebView: NSViewRepresentable {
    let url: URL
    let onFailure: (String) -> Void
    let onThemeChange: (String, String) -> Void

    func makeCoordinator() -> AtlasWebViewCoordinator {
        let coordinator = AtlasWebViewCoordinator()
        coordinator.onFailure = onFailure
        coordinator.onThemeChange = onThemeChange
        return coordinator
    }

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        // The dashboard starts Web Audio from its Play button. Keep WebKit's
        // media policy from leaving an AudioContext suspended in the native
        // shell after the click has already been received.
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.userContentController.add(context.coordinator, name: "atlasTheme")
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.setValue(false, forKey: "drawsBackground")
        webView.allowsBackForwardNavigationGestures = false
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        guard webView.url != url else { return }
        webView.load(URLRequest(url: url))
    }
}
