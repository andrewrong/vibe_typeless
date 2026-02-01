#!/bin/bash
set -e

echo "🔨 Building TypelessApp..."
swift build

echo "🔐 Signing with entitlements..."
codesign --force --deep --sign - \
  --entitlements TypelessApp.entitlements \
  .build/arm64-apple-macosx/debug/TypelessApp

echo "✅ Build complete!"
echo "📱 Binary entitlements:"
codesign -d --entitlements - .build/arm64-apple-macosx/debug/TypelessApp
