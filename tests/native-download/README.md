# Native download regression

On macOS, compile the production WebKit coordinator with this standalone entry
point, then run it from the repository root:

```sh
mkdir -p work/native-download-regression
swiftc -parse-as-library \
  Sources/ShapeNoteAtlas/Views/AtlasWebView.swift \
  tests/native-download/main.swift \
  -framework AppKit -framework SwiftUI -framework WebKit \
  -o work/native-download-regression/check
work/native-download-regression/check
```

The harness opens no window or panel. It runs a loopback HTTP server containing
only synthetic bytes and lets the coordinator select temporary destinations.
It covers actual WebKit navigation-action and MIME-response downloads, exact
saved bytes, cancellation, rejection of an existing file, a truncated transfer,
and the reader remaining usable. Direct validation checks cover existing
directories, symbolic links, and non-file URLs. Genuine page errors still reach
the page-recovery callback.

Native-window acceptance remains separate: click **Download editable MusicXML**
in the actual reader, confirm the save sheet and suggested filename, save to a
new path, and compare its bytes with the served asset. Cancel another download
and confirm that the same reader stays usable. Choose an existing filename and
confirm it is rejected without changing the existing file. External source PDF
links should continue to open through the existing system-browser route.

Downloads do not change source-publication or review status. This regression
does not establish source fidelity or publication eligibility.
