#!/usr/bin/env bash
# =============================================================================
# Lance Mon Pass Sanitaire directement sur un appareil connecté (USB ou Wi-Fi).
#
# Usage:
#   ./scripts/run_device.sh staging        # release sur api-staging
#   ./scripts/run_device.sh prod           # release sur api prod
#   ./scripts/run_device.sh staging debug  # debug (hot-reload activé)
#
# Différence avec build_apk.sh : ce script INSTALLE et LANCE en une étape,
# avec affichage des logs en temps réel. Idéal pour tester sur ton téléphone
# branché en USB depuis le Mac.
#
# Pré-requis :
#   - Téléphone branché en USB, débogage USB activé
#   - "flutter devices" doit lister l'appareil
# =============================================================================

set -euo pipefail

ENV="${1:-}"
MODE="${2:-release}"   # release par défaut, sinon "debug" ou "profile"

if [[ "$ENV" != "prod" && "$ENV" != "staging" ]]; then
  echo "❌ Usage : $0 <prod|staging> [release|debug|profile]"
  exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

case "$ENV" in
  prod)    SRC=".env.production" ;;
  staging) SRC=".env.staging"   ;;
esac

if [[ ! -f "$SRC" ]]; then
  echo "❌ $SRC introuvable. Vérifiez qu'il existe à la racine de mobile/."
  exit 1
fi

# Backup l'ancien .env pour restauration auto à la fin
if [[ -f .env ]]; then
  cp .env .env.backup
fi
cp "$SRC" .env
echo "✅ Environnement $ENV actif (depuis $SRC)"
echo "   $(grep API_MOBILE_BASE_URL .env | head -1)"
echo "   Mode : $MODE"
echo ""

# Vérifier qu'au moins un appareil est connecté
DEVICES=$(flutter devices 2>/dev/null | grep -E "android|ios" | head -5 || true)
if [[ -z "$DEVICES" ]]; then
  echo "⚠  Aucun appareil détecté."
  echo "   - Brancher le téléphone en USB"
  echo "   - Activer le débogage USB (Paramètres → Options développeur)"
  echo "   - Accepter l'invitation RSA sur le téléphone au premier branchement"
  echo ""
  echo "Lister manuellement : flutter devices"
  exit 1
fi
echo "📱 Appareil(s) détecté(s) :"
echo "$DEVICES"
echo ""

# Restaurer l'env précédent à la sortie même si flutter run est interrompu (Ctrl+C)
trap 'if [[ -f .env.backup ]]; then mv .env.backup .env; echo ""; echo "ℹ  .env précédent restauré"; fi' EXIT

# Lancer flutter run dans le mode choisi
echo "🚀 Lancement…"
flutter run --$MODE
