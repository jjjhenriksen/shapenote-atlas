# Native server lifecycle regression

On macOS, from the repository root:

```sh
mkdir -p work/native-lifecycle-regression
swiftc -parse-as-library \
  Sources/ShapeNoteAtlas/Models/AtlasAppModel.swift \
  Sources/ShapeNoteAtlas/Support/AtlasTheme.swift \
  Sources/ShapeNoteAtlas/Services/LocalDashboardServer.swift \
  tests/native-lifecycle/main.swift \
  -framework AppKit -framework Combine -framework SwiftUI \
  -o work/native-lifecycle-regression/check
work/native-lifecycle-regression/check
```

This uses the actual model, termination observer and Python server. It verifies
that a quit notification stops the owned child and closes its listening socket
while an unrelated server stays alive, a fresh model can own a new server, and
observer cleanup does not retain the model or its server. It launches no GUI.
Actual Command-Q and native-window reopen need separate app-bundle verification.
