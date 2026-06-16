#!/usr/bin/env bash
# Encode tous les fichiers sensibles en base64 prêts à être collés dans
# les secrets GitHub Actions. Imprime juste sur stdout, ne stocke rien.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "════════════════════════════════════════════════════"
echo "  Encode des secrets pour GitHub Actions"
echo "════════════════════════════════════════════════════"
echo ""

encode() {
  local label="$1"
  local path="$2"
  if [ -f "$path" ]; then
    echo "─── $label  ($path) ───"
    base64 -i "$path" | tr -d '\n'
    echo
    echo
  else
    echo "─── $label  ($path)  → ABSENT, à fournir ───"
    echo
  fi
}

encode "ANDROID_KEYSTORE_BASE64"        android/keys/release.keystore
encode "GOOGLE_SERVICES_JSON_BASE64"    android/app/google-services.json
encode "GOOGLE_SERVICES_PLIST_BASE64"   ios/Runner/GoogleService-Info.plist
encode "APPLE_CERT_BASE64"              ios/certs/distribution.p12
encode "APPLE_PROVISION_BASE64"         ios/certs/distribution.mobileprovision

echo ""
echo "Mots de passe à fournir manuellement dans les secrets :"
echo "  ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_ALIAS, ANDROID_KEY_PASSWORD"
echo "  APPLE_CERT_PASSWORD, APPLE_KEYCHAIN_PASSWORD"
echo ""
echo "→ Repository > Settings > Secrets and variables > Actions"
