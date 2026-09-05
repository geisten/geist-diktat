#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
APP='build/Geist Diktat.app'
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/runtime/bin" "$APP/Contents/Resources/runtime/share/geist-diktat"
xcrun swiftc -module-cache-path build/swift-module-cache -O macos/GeistDiktat.swift -o "$APP/Contents/MacOS/GeistDiktat" -framework AppKit -framework AVFoundation -framework ApplicationServices -framework Carbon
cp diktat packaging/geist-diktat "$APP/Contents/Resources/runtime/bin/"
cp runtime/*.py geistlib/tools/fetch_audio_tower.py geistlib/audio_test_data/mel_constants.bin "$APP/Contents/Resources/runtime/share/geist-diktat/"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>de.geisten.geist-diktat</string>
<key>CFBundleName</key><string>Geist Diktat</string>
<key>CFBundleExecutable</key><string>GeistDiktat</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleShortVersionString</key><string>0.2.0</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>LSUIElement</key><true/>
<key>NSMicrophoneUsageDescription</key><string>Lokales Diktieren; Audiodaten werden nicht hochgeladen.</string>
</dict></plist>
PLIST
codesign --force --deep --sign "${GEIST_SIGN_IDENTITY:--}" "$APP"
"$APP/Contents/MacOS/GeistDiktat" --self-test
printf 'Built %s (not notarized; capture requires sox or ffmpeg and Python 3).\n' "$APP"
