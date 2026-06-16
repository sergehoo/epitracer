#!/usr/bin/env bash
# Build Android release local (AAB + APK universel).
# Prérequis : Flutter SDK installé, JDK 17, key.properties configuré.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "▶ pub get + codegen"
flutter pub get
dart run build_runner build --delete-conflicting-outputs

echo "▶ flutter clean"
flutter clean

echo "▶ Vérification key.properties"
if [ ! -f android/key.properties ]; then
  echo "❌ android/key.properties manquant — voir android/key.properties.example"
  exit 1
fi

if [ ! -f android/app/google-services.json ]; then
  echo "⚠️  android/app/google-services.json absent — push FCM désactivé"
fi

echo "▶ Build AAB (Play Store)"
flutter build appbundle --release

echo "▶ Build APK universel (sideload)"
flutter build apk --release

echo ""
echo "✅ Builds générés :"
ls -lh build/app/outputs/bundle/release/*.aab 2>/dev/null || true
ls -lh build/app/outputs/flutter-apk/*-release.apk 2>/dev/null || true
