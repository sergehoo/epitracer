#!/usr/bin/env bash
# =============================================================================
# Build d'un APK Mon Pass Sanitaire pour PROD ou STAGING.
#
# Usage:
#   ./scripts/build_apk.sh staging       # APK staging → api-staging.veillesanitaire.com
#   ./scripts/build_apk.sh prod          # APK prod    → api.veillesanitaire.com
#   ./scripts/build_apk.sh staging --aab # AAB Play Store au lieu d'APK
#
# Sortie :
#   build/app/outputs/flutter-apk/app-release-{ENV}.apk
#   ou (avec --aab) build/app/outputs/bundle/release/app-release-{ENV}.aab
#
# La logique : on COPIE .env.production OU .env.staging vers .env (lu par
# flutter_dotenv au runtime), on lance le build, puis on renomme l'artefact
# avec le suffixe d'environnement pour éviter toute confusion.
# =============================================================================

set -euo pipefail

ENV="${1:-}"
SHIP_AAB=0

if [[ "${2:-}" == "--aab" ]]; then
  SHIP_AAB=1
fi

if [[ "$ENV" != "prod" && "$ENV" != "staging" ]]; then
  echo "❌ Usage : $0 <prod|staging> [--aab]"
  exit 1
fi

# Se placer dans le dossier mobile (parent du dossier scripts)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Choisir le bon fichier source
case "$ENV" in
  prod)
    SRC=".env.production"
    SUFFIX="prod"
    ;;
  staging)
    SRC=".env.staging"
    SUFFIX="staging"
    ;;
esac

if [[ ! -f "$SRC" ]]; then
  echo "❌ Fichier $SRC introuvable. Vérifiez qu'il existe à la racine de mobile/."
  exit 1
fi

# Backup l'ancien .env (s'il existe) pour pouvoir le restaurer
if [[ -f .env ]]; then
  cp .env .env.backup
fi

# Copier la config d'environnement vers .env
cp "$SRC" .env
echo "✅ Configuration $SUFFIX active (depuis $SRC)"
echo "   API : $(grep API_MOBILE_BASE_URL .env | head -1)"

# Lancer le build
if [[ $SHIP_AAB -eq 1 ]]; then
  echo "🏗  Build AAB release ($SUFFIX) en cours..."
  flutter build appbundle --release
  OUT_SRC="build/app/outputs/bundle/release/app-release.aab"
  OUT_DST="build/app/outputs/bundle/release/app-release-${SUFFIX}.aab"
else
  echo "🏗  Build APK release ($SUFFIX) en cours..."
  flutter build apk --release
  OUT_SRC="build/app/outputs/flutter-apk/app-release.apk"
  OUT_DST="build/app/outputs/flutter-apk/app-release-${SUFFIX}.apk"
fi

# Renommer l'artefact pour qu'on ne mélange pas prod et staging dans le dossier
if [[ -f "$OUT_SRC" ]]; then
  mv "$OUT_SRC" "$OUT_DST"
  echo ""
  echo "✅ Build terminé : $OUT_DST"
  ls -lh "$OUT_DST"
else
  echo "⚠  Build non trouvé à $OUT_SRC — vérifier la sortie ci-dessus."
  exit 1
fi

# Restaurer l'ancien .env s'il existait
if [[ -f .env.backup ]]; then
  mv .env.backup .env
  echo "ℹ  .env précédent restauré"
fi

echo ""
echo "Pour installer sur un device connecté en ADB :"
echo "  adb install -r $OUT_DST"
