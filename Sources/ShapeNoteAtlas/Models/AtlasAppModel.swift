import Combine
import Foundation

@MainActor
final class AtlasAppModel: ObservableObject {
    @Published var url: URL?
    @Published var errorMessage: String?
    @Published var palette = AtlasTheme.palette(bookId: "sh1991", mode: "dark")

    private let server = LocalDashboardServer()

    func updateTheme(bookId: String, mode: String) {
        palette = AtlasTheme.palette(bookId: bookId, mode: mode)
    }

    func start() {
        guard url == nil, errorMessage == nil else { return }
        guard let resourceRoot = Bundle.main.resourceURL else {
            errorMessage = "The atlas resources could not be found."
            return
        }

        let webRoot = resourceRoot.appendingPathComponent("web", isDirectory: true)
        guard FileManager.default.fileExists(atPath: webRoot.appendingPathComponent("index.html").path) else {
            errorMessage = "The atlas web bundle is missing. Rebuild the app and try again."
            return
        }

        server.start(root: webRoot) { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let url):
                var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
                components?.queryItems = [URLQueryItem(name: "nativeShell", value: "1")]
                self.url = components?.url ?? url
            case .failure(let error):
                self.errorMessage = "The local atlas service could not start. \(error.localizedDescription)"
            }
        }
    }

    func retry() {
        server.stop()
        url = nil
        errorMessage = nil
        start()
    }

    deinit {
        server.stop()
    }
}
