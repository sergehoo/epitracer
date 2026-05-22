#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Export sécurisé des clés cryptographiques d'EpiTrace
# (Ed25519 pour les pass + VAPID pour Web Push).
#
# Crée un fichier `epitrace-keys-YYYYMMDD-HHMMSS.tar.gz.gpg` chiffré
# AES-256 avec une passphrase générée aléatoirement. Affiche la
# passphrase une seule fois à l'écran — à copier-coller IMMÉDIATEMENT
# dans 1Password Business (ou équivalent gestionnaire de secrets).
#
# Le script :
#   1. crée un dossier temporaire (mode 0700, root only)
#   2. extrait les 4 fichiers .pem depuis le container `web`
#   3. génère un checksum SHA256
#   4. génère une passphrase 32 caractères aléatoires
#   5. chiffre l'archive avec GPG --batch (compatible SSH sans TTY)
#   6. VÉRIFIE que le .gpg existe et fait au moins 1 KB
#   7. supprime les fichiers en clair via `shred`
#   8. affiche le chemin du .gpg + passphrase
#
# Usage :
#   sudo bash scripts/export_keys_secure.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$REPO_DIR"

COMPOSE_FILE_BASE=${COMPOSE_FILE_BASE:-docker-compose.yml}
COMPOSE_FILE_PROD=${COMPOSE_FILE_PROD:-docker-compose.prod.yml}
COMPOSE_PROJECT=${COMPOSE_PROJECT:-$(basename "$REPO_DIR")}
WEB_SERVICE=${WEB_SERVICE:-web}

OUTPUT_DIR=${OUTPUT_DIR:-$HOME}
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE_NAME="epitrace-keys-$TIMESTAMP.tar.gz.gpg"
OUTPUT_FILE="$OUTPUT_DIR/$ARCHIVE_NAME"

WORK_DIR=$(mktemp -d -t epitrace-keys-XXXXXXXX)
chmod 700 "$WORK_DIR"

cleanup() {
  # Toujours nettoyer le dossier temporaire (même si erreur)
  if [ -d "$WORK_DIR" ]; then
    find "$WORK_DIR" -type f -exec shred -uvz -n 2 {} + 2>/dev/null || true
    rm -rf "$WORK_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Extraction des clés depuis le container '$WEB_SERVICE'…"
for k in healthpass_ed25519_private.pem healthpass_ed25519_public.pem \
         vapid_private.pem vapid_public.pem; do
  docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
    --project-name "$COMPOSE_PROJECT" \
    exec -T "$WEB_SERVICE" cat "/app/keys/$k" > "$WORK_DIR/$k"

  if [ ! -s "$WORK_DIR/$k" ]; then
    echo "ERREUR : '$k' est vide ou inaccessible. Annulation."
    exit 1
  fi
done

chmod 600 "$WORK_DIR"/*_private.pem
chmod 644 "$WORK_DIR"/*_public.pem
( cd "$WORK_DIR" && sha256sum *.pem > CHECKSUMS.sha256 )

echo "==> Génération d'une passphrase aléatoire 32 caractères…"
# 32 chars URL-safe (lettres+chiffres+_-) = ~190 bits d'entropie
PASSPHRASE=$(openssl rand -base64 32 | tr -d '/=+' | cut -c1-32)

echo "==> Chiffrement GPG AES-256 (--batch, sans TTY)…"
( cd "$WORK_DIR" && tar czf - *.pem CHECKSUMS.sha256 ) \
  | gpg --batch --yes --pinentry-mode loopback \
        --passphrase "$PASSPHRASE" \
        --symmetric --cipher-algo AES256 \
        --output "$OUTPUT_FILE"

# ---- Vérification stricte ----
if [ ! -s "$OUTPUT_FILE" ]; then
  echo "ERREUR : l'archive chiffrée n'a pas été créée. Annulation."
  exit 2
fi
SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || stat -f%z "$OUTPUT_FILE")
if [ "$SIZE" -lt 500 ]; then
  echo "ERREUR : archive trop petite ($SIZE bytes) — fichier probablement corrompu."
  rm -f "$OUTPUT_FILE"
  exit 3
fi
chmod 600 "$OUTPUT_FILE"

echo
echo "========================================================================"
echo "✅ EXPORT RÉUSSI"
echo "========================================================================"
echo
echo "Archive chiffrée : $OUTPUT_FILE"
echo "Taille           : $SIZE octets"
echo
echo "🔑 PASSPHRASE (à STOCKER IMMÉDIATEMENT dans 1Password Business) :"
echo
echo "    $PASSPHRASE"
echo
echo "⚠️  Cette passphrase ne sera PAS réaffichée. Si tu la perds, l'archive"
echo "    est définitivement irrécupérable."
echo
echo "Prochaines étapes :"
echo "  1. Copie la passphrase ci-dessus dans 1Password / Vault"
echo "     (item 'EpiTrace Master Keys $TIMESTAMP')"
echo "  2. Télécharge $OUTPUT_FILE sur ton poste sécurisé :"
echo "       scp $(whoami)@$(hostname -I | awk '{print $1}'):$OUTPUT_FILE ."
echo "  3. Distribue en 3 copies :"
echo "       - 1Password Business vault (déjà fait avec la passphrase)"
echo "       - USB hardware-encrypted (Kingston IronKey), coffre INHP"
echo "       - Tiers de confiance (DPO / notaire / ANCS)"
echo "  4. Note la date et le SHA256 de l'archive :"
sha256sum "$OUTPUT_FILE"
echo
echo "========================================================================"
