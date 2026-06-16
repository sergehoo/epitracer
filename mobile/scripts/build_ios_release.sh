#!/usr/bin/env bash
# Build iOS release local (IPA pour App Store).
# Prérequis : macOS, Xcode, certificat de signing + provisioning profile
# installés dans le trousseau, ExportOptions.plist rempli.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ macOS requis pour builder iOS."
  exit 1
fi

echo "▶ pub get + codegen"
flutter pub get
dart run build_runner build --delete-conflicting-outputs

if [ ! -f ios/ExportOptions.plist ]; then
  echo "❌ ios/ExportOptions.plist manquant — voir ios/ExportOptions.plist.template"
  exit 1
fi

if [ ! -f ios/Runner/GoogleService-Info.plist ]; then
  echo "⚠️  GoogleService-Info.plist absent — push FCM désactivé"
fi

echo "▶ pod install"
(cd ios && pod install --repo-update)

echo "▶ flutter build ipa"
flutter build ipa --release --export-options-plist=ios/ExportOptions.plist

echo ""
echo "✅ IPA générée :"
ls -lh build/ios/ipa/*.ipa 2>/dev/null || true
echo ""
echo "Upload App Store :"
echo "  xcrun altool --upload-app -f build/ios/ipa/*.ipa \\"
echo "    -u <APPLE_ID> -p <APP_SPECIFIC_PASSWORD>"
