# Native navigation regression

On macOS, compile the actual model and WebKit coordinator with the standalone
regression entry point, excluding the production app entry point:

```sh
mkdir -p work/native-navigation-regression
swiftc -parse-as-library \
  Sources/ShapeNoteAtlas/Models/AtlasAppModel.swift \
  Sources/ShapeNoteAtlas/Support/AtlasTheme.swift \
  Sources/ShapeNoteAtlas/Services/LocalDashboardServer.swift \
  Sources/ShapeNoteAtlas/Views/AtlasWebView.swift \
  tests/native-navigation/main.swift \
  -framework AppKit -framework Combine -framework SwiftUI -framework WebKit \
  -o work/native-navigation-regression/check
work/native-navigation-regression/check
```

The checks cover a failure after URL assignment, both WebKit failure callbacks,
expected URL cancellation, and an unrelated error domain using the same numeric
code. They call the coordinator directly; they do not prove native window layout,
actual navigation, server recovery or catalogue/playback acceptance.

For native-window verification, stage a separate production app bundle with a
unique bundle identifier and a synthetic `Resources/web/index.html`. Open it with
`open -n`, stop only its owned child server, and follow a local link. Confirm the
visible error and Try Again button, then confirm retry returns to the bundled
fixture. A fixture with a failing iframe should leave its healthy main frame
visible. Preserve screenshots and label this synthetic-window coverage separately
from a full production reader acceptance run.
