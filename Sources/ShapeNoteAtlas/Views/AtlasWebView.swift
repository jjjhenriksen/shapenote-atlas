import AppKit
import SwiftUI
import WebKit

final class AtlasWebViewCoordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler, WKDownloadDelegate, NSOpenSavePanelDelegate {
    var onFailure: ((String) -> Void)?
    var onThemeChange: ((String, String) -> Void)?
    var onDownloadFailure: ((Error) -> Void)?
    var selectDownloadDestination: ((String, WKWebView?, @escaping (URL?) -> Void) -> Void)?

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        decisionHandler(navigationAction.shouldPerformDownload ? .download : .allow)
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationResponse: WKNavigationResponse,
        decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
    ) {
        decisionHandler(navigationResponse.canShowMIMEType ? .allow : .download)
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }

    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }

    func download(
        _ download: WKDownload,
        decideDestinationUsing response: URLResponse,
        suggestedFilename: String,
        completionHandler: @escaping (URL?) -> Void
    ) {
        let completeSelection: (URL?) -> Void = { [self] destination in
            guard let destination else {
                completionHandler(nil)
                return
            }
            do {
                // WebKit writes the response itself, without changing score bytes.
                // Its destination must not already exist, even after a save panel.
                try Self.validateDownloadDestination(destination)
                completionHandler(destination)
            } catch {
                completionHandler(nil)
                reportDownloadFailure(error, webView: download.webView)
            }
        }
        if let selectDownloadDestination {
            selectDownloadDestination(suggestedFilename, download.webView, completeSelection)
            return
        }

        let panel = NSSavePanel()
        panel.title = "Save Download"
        panel.nameFieldStringValue = (suggestedFilename as NSString).lastPathComponent
        panel.canCreateDirectories = true
        panel.isExtensionHidden = false
        panel.delegate = self
        let didChoose: (NSApplication.ModalResponse) -> Void = { result in
            completeSelection(result == .OK ? panel.url : nil)
        }
        if let window = download.webView?.window {
            panel.beginSheetModal(for: window, completionHandler: didChoose)
        } else {
            panel.begin(completionHandler: didChoose)
        }
    }

    func panel(_ sender: Any, validate url: URL) throws {
        try Self.validateDownloadDestination(url)
    }

    static func validateDownloadDestination(_ url: URL) throws {
        guard url.isFileURL else {
            throw NSError(domain: NSCocoaErrorDomain, code: NSFileWriteUnsupportedSchemeError,
                          userInfo: [NSLocalizedDescriptionKey: "Choose a local folder for the download."])
        }
        // attributesOfItem also finds a symbolic link whose target is missing.
        if (try? FileManager.default.attributesOfItem(atPath: url.path)) != nil {
            throw NSError(domain: NSCocoaErrorDomain, code: NSFileWriteFileExistsError,
                          userInfo: [NSLocalizedDescriptionKey: "A file already exists at this location. Choose a different name to keep the existing file."])
        }
    }

    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        let failure = error as NSError
        guard failure.domain != NSURLErrorDomain || failure.code != NSURLErrorCancelled else { return }
        reportDownloadFailure(error, webView: download.webView)
    }

    private func reportDownloadFailure(_ error: Error, webView: WKWebView?) {
        if let onDownloadFailure {
            onDownloadFailure(error)
            return
        }
        let alert = NSAlert()
        alert.messageText = "The download could not be saved."
        alert.informativeText = error.localizedDescription
        alert.alertStyle = .warning
        if let window = webView?.window {
            alert.beginSheetModal(for: window)
        } else {
            alert.runModal()
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        reportNavigationFailure(error)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        reportNavigationFailure(error)
    }

    private func reportNavigationFailure(_ error: Error) {
        // These WKNavigationDelegate failures apply to the main frame. A load
        // cancelled by another navigation is expected and needs no retry UI.
        let failure = error as NSError
        guard failure.domain != NSURLErrorDomain || failure.code != NSURLErrorCancelled else { return }
        // Legacy WebKit policy-interruption error when a navigation becomes a
        // download (WebKitErrors.h: WebKitErrorFrameLoadInterruptedByPolicyChange).
        guard failure.domain != "WebKitErrorDomain" || failure.code != 102 else { return }
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
