import Foundation

let log = BoundedDashboardLog()
log.append(Data(repeating: 65, count: 100_000))
log.append(Data("latest diagnostic".utf8))
precondition(log.text.utf8.count <= 8192)
precondition(log.text.hasSuffix("latest diagnostic"))

let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
try Data("server regression fixture".utf8).write(to: root.appendingPathComponent("index.html"))
defer { try? FileManager.default.removeItem(at: root) }
let server = LocalDashboardServer()
var startupError: Error?
server.start(root: root) { result in
    if case .failure(let error) = result { startupError = error }
}
let deadline = Date().addingTimeInterval(10)
while server.url == nil && startupError == nil && Date() < deadline {
    RunLoop.current.run(until: Date().addingTimeInterval(0.01))
}
if let startupError { fatalError("Startup failed: \(startupError)") }
guard let url = server.url else { fatalError("Startup timed out") }
defer { server.stop() }
for index in 1...2201 {
    let semaphore = DispatchSemaphore(value: 0)
    let result = RequestResult()
    URLSession.shared.dataTask(with: url) { _, response, error in
        result.record(code: (response as? HTTPURLResponse)?.statusCode, error: error)
        semaphore.signal()
    }.resume()
    precondition(semaphore.wait(timeout: .now() + 5) == .success, "Request \(index) hung")
    precondition(result.succeeded, "Request \(index) failed")
}
print("2201 real server requests passed; diagnostic tail remains bounded.")

final class RequestResult: @unchecked Sendable {
    private let lock = NSLock()
    private var valid = false
    func record(code: Int?, error: Error?) {
        lock.lock(); defer { lock.unlock() }
        valid = code == 200 && error == nil
    }
    var succeeded: Bool {
        lock.lock(); defer { lock.unlock() }
        return valid
    }
}
