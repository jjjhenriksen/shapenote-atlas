import Foundation

final class LocalDashboardServer {
    private(set) var process: Process?
    private(set) var port: Int?

    var url: URL? {
        guard let port else { return nil }
        return URL(string: "http://127.0.0.1:\(port)/")
    }

    func start(root: URL, completion: @escaping (Result<URL, Error>) -> Void) {
        guard process == nil else { return }

        let server = Process()
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        var outputBuffer = ""
        var didComplete = false
        let pythonServer = """
        import functools
        import http.server
        import sys
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1])
        server = http.server.ThreadingHTTPServer((\"127.0.0.1\", 0), handler)
        print(server.server_port, flush=True)
        server.serve_forever()
        """
        server.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        server.arguments = [
            "-c", pythonServer, root.path
        ]
        server.standardOutput = outputPipe
        server.standardError = errorPipe
        server.terminationHandler = { _ in
            outputPipe.fileHandleForReading.readabilityHandler = nil
            let detail = String(data: errorPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)?
                .trimmingCharacters(in: .whitespacesAndNewlines)
            DispatchQueue.main.async {
                guard !didComplete else { return }
                didComplete = true
                completion(.failure(LocalDashboardServerError.terminated(detail)))
            }
        }

        outputPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            outputBuffer += text
            guard let line = outputBuffer.split(whereSeparator: \.isNewline).first,
                  let port = Int(line.trimmingCharacters(in: .whitespacesAndNewlines)) else { return }

            DispatchQueue.main.async {
                guard let self, !didComplete else { return }
                didComplete = true
                self.port = port
                outputPipe.fileHandleForReading.readabilityHandler = nil
                if let url = self.url {
                    completion(.success(url))
                } else {
                    completion(.failure(LocalDashboardServerError.invalidAddress))
                }
            }
        }

        do {
            try server.run()
            process = server
        } catch {
            process = nil
            outputPipe.fileHandleForReading.readabilityHandler = nil
            completion(.failure(error))
        }
    }

    func stop() {
        guard let process else { return }
        if process.isRunning { process.terminate() }
        self.process = nil
        port = nil
    }
}

private enum LocalDashboardServerError: LocalizedError {
    case terminated(String?)
    case invalidAddress

    var errorDescription: String? {
        switch self {
        case .terminated(let detail):
            if let detail, !detail.isEmpty {
                return "The local atlas service exited before it could accept connections. \(detail)"
            }
            return "The local atlas service exited before it could accept connections."
        case .invalidAddress:
            return "The local atlas service did not report a usable address."
        }
    }
}
