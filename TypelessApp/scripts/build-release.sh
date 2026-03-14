#!/bin/bash
#
# Build Typeless macOS App for Distribution
# Creates a release build and packages it as a .app bundle
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building Typeless for Release${NC}"
echo "========================================"

# Configuration
APP_NAME="Typeless"
BUNDLE_ID="com.typeless.app"
VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "1.0.0")
BUILD_DIR=".build/release"
APP_BUNDLE="${APP_NAME}.app"

echo -e "\n${YELLOW}📦 Configuration:${NC}"
echo "  App Name: ${APP_NAME}"
echo "  Bundle ID: ${BUNDLE_ID}"
echo "  Version: ${VERSION}"

# Clean previous build
echo -e "\n${YELLOW}🧹 Cleaning previous build...${NC}"
rm -rf "${BUILD_DIR}"
rm -rf "${APP_BUNDLE}"
rm -f "${APP_NAME}-${VERSION}.dmg"
rm -f "${APP_NAME}-${VERSION}.zip"

# Build release version
echo -e "\n${YELLOW}🔨 Building release binary...${NC}"
swift build -c release --arch arm64

# Check if build succeeded
if [ ! -f "${BUILD_DIR}/TypelessApp" ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build successful!${NC}"

# Create .app bundle structure
echo -e "\n${YELLOW}📁 Creating .app bundle...${NC}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

# Copy binary
cp "${BUILD_DIR}/TypelessApp" "${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"
chmod +x "${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"

# Create Info.plist
cat > "${APP_BUNDLE}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Typeless needs microphone access for voice transcription.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>Typeless needs accessibility access to inject transcribed text.</string>
</dict>
</plist>
EOF

# Create PkgInfo
echo -n "APPL????" > "${APP_BUNDLE}/Contents/PkgInfo"

# Try to copy icon if it exists
if [ -f "Resources/AppIcon.icns" ]; then
    cp "Resources/AppIcon.icns" "${APP_BUNDLE}/Contents/Resources/"
    echo -e "${GREEN}✅ Icon added${NC}"
else
    echo -e "${YELLOW}⚠️  No icon found (Resources/AppIcon.icns)${NC}"
fi

echo -e "${GREEN}✅ .app bundle created: ${APP_BUNDLE}${NC}"

# Sign the app (optional, for local use ad-hoc signing is fine)
echo -e "\n${YELLOW}🔏 Signing app...${NC}"
codesign --force --deep --sign - "${APP_BUNDLE}" 2>/dev/null || echo -e "${YELLOW}⚠️  Signing skipped (codesign not available)${NC}"

# Verify app
echo -e "\n${YELLOW}🔍 Verifying app bundle...${NC}"
if [ -d "${APP_BUNDLE}" ]; then
    echo -e "${GREEN}✅ App bundle structure OK${NC}"
    ls -lh "${APP_BUNDLE}/Contents/MacOS/"
else
    echo -e "${RED}❌ App bundle creation failed${NC}"
    exit 1
fi

# Create distribution packages
echo -e "\n${YELLOW}📦 Creating distribution packages...${NC}"

# Option 1: ZIP archive
zip -r "${APP_NAME}-${VERSION}.zip" "${APP_BUNDLE}"
echo -e "${GREEN}✅ Created: ${APP_NAME}-${VERSION}.zip${NC}"

# Option 2: DMG (if create-dmg is installed)
if command -v create-dmg &> /dev/null; then
    echo -e "\n${YELLOW}💿 Creating DMG...${NC}"
    create-dmg \
        --volname "${APP_NAME} Installer" \
        --volicon "Resources/AppIcon.icns" 2>/dev/null || true \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --app-drop-link 600 185 \
        "${APP_NAME}-${VERSION}.dmg" \
        "${APP_BUNDLE}" 2>/dev/null || echo -e "${YELLOW}⚠️  DMG creation skipped${NC}"
else
    echo -e "${YELLOW}ℹ️  create-dmg not installed, skipping DMG creation${NC}"
    echo "   Install with: brew install create-dmg"
fi

# Summary
echo -e "\n${GREEN}🎉 Build Complete!${NC}"
echo "========================================"
echo -e "${GREEN}Output files:${NC}"
echo "  📱 ${APP_BUNDLE}/"
echo "  📦 ${APP_NAME}-${VERSION}.zip"
if [ -f "${APP_NAME}-${VERSION}.dmg" ]; then
    echo "  💿 ${APP_NAME}-${VERSION}.dmg"
fi
echo ""
echo -e "${YELLOW}Installation Instructions:${NC}"
echo "  1. Double-click ${APP_NAME}.app to run"
echo "  2. Or drag ${APP_NAME}.app to /Applications"
echo "  3. If blocked by Gatekeeper, right-click → Open"
echo ""
echo -e "${YELLOW}System Requirements:${NC}"
echo "  - macOS 14.0 (Sonoma) or later"
echo "  - Apple Silicon (M1/M2/M3)"
echo "  - Python backend must be running"
