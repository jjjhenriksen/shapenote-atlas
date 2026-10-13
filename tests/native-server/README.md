# Native server regression

On macOS with the Swift toolchain installed, from the repository root:

```sh
mkdir -p work/native-server-regression
swiftc -swift-version 5 Sources/ShapeNoteAtlas/Services/LocalDashboardServer.swift tests/native-server/main.swift -o work/native-server-regression/check
work/native-server-regression/check
```

This compiles the actual Foundation server class, verifies its bounded log tail,
and serves 2,201 HTTP requests from a temporary synthetic directory. It stops
its child server and removes the fixture afterwards. It does not launch or
verify the native app window. This macOS check is separate from clone-safe
Linux reader checks and source-archive verification.
