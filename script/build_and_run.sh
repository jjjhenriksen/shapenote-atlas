#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-run}"
PRODUCT_NAME="ShapeNoteAtlas"
APP_NAME="The Shape-Note Atlas"
BUNDLE_ID="com.sacredharp.shapenoteatlas"
MIN_SYSTEM_VERSION="13.0"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/outputs"
APP_BUNDLE="$OUTPUT_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
APP_BINARY="$APP_MACOS/$PRODUCT_NAME"
INFO_PLIST="$APP_CONTENTS/Info.plist"
ICON_SOURCE="$ROOT_DIR/Assets/ShapeNoteAtlas.svg"
ICONSET_DIR="$ROOT_DIR/work/ShapeNoteAtlas.iconset"
ICON_PNG="$ROOT_DIR/work/ShapeNoteAtlas-1024.png"

cleanup_local_servers() {
  pkill -f "ThreadingHTTPServer.*$APP_RESOURCES/web" >/dev/null 2>&1 || true
}

pkill -x "$PRODUCT_NAME" >/dev/null 2>&1 || true
cleanup_local_servers
pkill -f 'http.server 48721' >/dev/null 2>&1 || true

npm run build
SWIFT_BUILD_DIR="$ROOT_DIR/.build/shape-note-atlas"
mkdir -p "$SWIFT_BUILD_DIR"
SWIFT_SOURCES=()
while IFS= read -r source_file; do
  SWIFT_SOURCES+=("$source_file")
done < <(find "$ROOT_DIR/Sources/ShapeNoteAtlas" -name '*.swift' -print)
swiftc -parse-as-library "${SWIFT_SOURCES[@]}" \
  -o "$SWIFT_BUILD_DIR/$PRODUCT_NAME" \
  -framework AppKit -framework Combine -framework SwiftUI -framework WebKit

BUILD_BINARY="$SWIFT_BUILD_DIR/$PRODUCT_NAME"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_MACOS" "$APP_RESOURCES/web"
cp "$BUILD_BINARY" "$APP_BINARY"
chmod +x "$APP_BINARY"
cp -R "$ROOT_DIR/dist/." "$APP_RESOURCES/web/"

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
sips -s format png "$ICON_SOURCE" --out "$ICON_PNG" >/dev/null
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
iconutil -c icns "$ICONSET_DIR" -o "$APP_RESOURCES/ShapeNoteAtlas.icns"

cat >"$INFO_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>$PRODUCT_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>$BUNDLE_ID</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>
  <string>ShapeNoteAtlas</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>$MIN_SYSTEM_VERSION</string>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST

open_app() {
  /usr/bin/open -n "$APP_BUNDLE"
}

case "$MODE" in
  run)
    open_app
    ;;
  --debug|debug)
    lldb -- "$APP_BINARY"
    ;;
  --logs|logs)
    open_app
    /usr/bin/log stream --info --style compact --predicate "process == \"$PRODUCT_NAME\""
    ;;
  --telemetry|telemetry)
    open_app
    /usr/bin/log stream --info --style compact --predicate "subsystem == \"$BUNDLE_ID\""
    ;;
  --verify|verify)
    open_app
    sleep 1
    pgrep -x "$PRODUCT_NAME" >/dev/null
    ;;
  *)
    echo "usage: $0 [run|--debug|--logs|--telemetry|--verify]" >&2
    exit 2
    ;;
esac
