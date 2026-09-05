#!/usr/bin/env bash
set -euo pipefail

# Safe, non-launching package builder. Every run is staged in a fresh owned
# work directory; it never kills or replaces a running app.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="$ROOT_DIR/work/agent-09-startup"
mkdir -p "$WORK_ROOT"
RUN_DIR="$(mktemp -d "$WORK_ROOT/package.XXXXXX")"
APP_NAME="The Shape-Note Atlas"
PRODUCT_NAME="ShapeNoteAtlas"
APP_BUNDLE="$RUN_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
DIST_DIR="$RUN_DIR/dist"
BUILD_TIMEOUT_SECONDS="${ATLAS_BUILD_TIMEOUT_SECONDS:-180}"

python3 "$ROOT_DIR/scripts/run_bounded_command.py" \
  --timeout "$BUILD_TIMEOUT_SECONDS" -- \
  env ATLAS_PUBLIC_DIR="$ROOT_DIR/public" npm --prefix "$ROOT_DIR" run build -- --outDir "$DIST_DIR"
mkdir -p "$APP_MACOS" "$APP_RESOURCES/web"

SWIFT_BUILD_DIR="$RUN_DIR/swift-build"
mkdir -p "$SWIFT_BUILD_DIR"
SWIFT_SOURCES=()
while IFS= read -r source_file; do
  SWIFT_SOURCES+=("$source_file")
done < <(find "$ROOT_DIR/Sources/ShapeNoteAtlas" -name '*.swift' -print)
swiftc -parse-as-library "${SWIFT_SOURCES[@]}" -o "$SWIFT_BUILD_DIR/$PRODUCT_NAME" \
  -framework AppKit -framework Combine -framework SwiftUI -framework WebKit
cp "$SWIFT_BUILD_DIR/$PRODUCT_NAME" "$APP_MACOS/$PRODUCT_NAME"
chmod +x "$APP_MACOS/$PRODUCT_NAME"
cp -R "$DIST_DIR/." "$APP_RESOURCES/web/"

ICONSET_DIR="$RUN_DIR/ShapeNoteAtlas.iconset"
ICON_PNG="$RUN_DIR/ShapeNoteAtlas-1024.png"
mkdir -p "$ICONSET_DIR"
sips -s format png "$ROOT_DIR/Assets/ShapeNoteAtlas.svg" --out "$ICON_PNG" >/dev/null
make_icon() {
  local size="$1"
  local filename="$2"
  sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET_DIR/$filename" >/dev/null
}
make_icon 16 icon_16x16.png
make_icon 32 icon_16x16@2x.png
make_icon 32 icon_32x32.png
make_icon 64 icon_32x32@2x.png
make_icon 128 icon_128x128.png
make_icon 256 icon_128x128@2x.png
make_icon 256 icon_256x256.png
make_icon 512 icon_256x256@2x.png
make_icon 512 icon_512x512.png
make_icon 1024 icon_512x512@2x.png
if ! iconutil -c icns "$ICONSET_DIR" -o "$APP_RESOURCES/ShapeNoteAtlas.icns"; then
  echo "warning: iconutil could not build the optional app icon; continuing without it" >&2
fi

cat >"$APP_CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>$PRODUCT_NAME</string>
  <key>CFBundleIdentifier</key><string>com.sacredharp.shapenoteatlas</string>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
PLIST

printf '%s\n' "$APP_BUNDLE"
