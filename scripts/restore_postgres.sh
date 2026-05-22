#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Restauration PostgreSQL d'EpiTrace depuis un dump compressé.
#
# Usage :
#   bash scripts/restore_postgres.sh /backups/epitrace-20260521-020000.sql.gz
#   bash scripts/restore_postgres.sh /backups/latest.sql.gz --force
#
# IMPORTANT :
# - cette commande DROP et recrée la base. Toutes les données actuelles
#   seront ÉCRASÉES. Confirmer interactivement (sauf --force).
# - À utiliser en environnement de staging d'abord pour tester !
# ---------------------------------------------------------------------------
set -euo pipefail

DUMP_FILE=${1:-}
FORCE=${2:-}

[ -z "$DUMP_FILE" ] && { echo "Usage: $0 <dump.sql.gz> [--force]"; exit 64; }
[ ! -r "$DUMP_FILE" ] && { echo "Fichier introuvable : $DUMP_FILE"; exit 66; }

# ---- Découverte du repo + lecture sélective du .env ----
# On ne source PAS .env (apostrophes/espaces dans certaines valeurs).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$REPO_DIR"

read_env_var() {
  local key="$1"
  local file="${2:-$REPO_DIR/.env}"
  [ -f "$file" ] || return 0
  grep -E "^${key}=" "$file" | head -n 1 | sed -E "s/^${key}=//; s/^['\"]//; s/['\"]\$//"
}

if [ -f "$REPO_DIR/.env" ]; then
  POSTGRES_USER=${POSTGRES_USER:-$(read_env_var POSTGRES_USER)}
  POSTGRES_DB=${POSTGRES_DB:-$(read_env_var POSTGRES_DB)}
  POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$(read_env_var POSTGRES_PASSWORD)}
fi

COMPOSE_FILE_BASE=${COMPOSE_FILE_BASE:-docker-compose.yml}
COMPOSE_FILE_PROD=${COMPOSE_FILE_PROD:-docker-compose.prod.yml}
COMPOSE_PROJECT=${COMPOSE_PROJECT:-$(basename "$REPO_DIR")}
DB_SERVICE=${DB_SERVICE:-db}
# Auto-detect depuis le container si pas dans .env
if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
  DETECTED_USER=$(docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
                   --project-name "$COMPOSE_PROJECT" \
                   exec -T "$DB_SERVICE" \
                   sh -c 'echo $POSTGRES_USER' 2>/dev/null | tr -d '\r')
  DETECTED_DB=$(docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
                  --project-name "$COMPOSE_PROJECT" \
                  exec -T "$DB_SERVICE" \
                  sh -c 'echo $POSTGRES_DB' 2>/dev/null | tr -d '\r')
  POSTGRES_USER=${POSTGRES_USER:-$DETECTED_USER}
  POSTGRES_DB=${POSTGRES_DB:-$DETECTED_DB}
fi
DB_USER=${POSTGRES_USER:-epitrace}
DB_NAME=${POSTGRES_DB:-epitrace}

# ---- Confirmation interactive ----
if [ "$FORCE" != "--force" ]; then
  echo "⚠️  Vous allez ÉCRASER la base '$DB_NAME' avec le contenu de :"
  echo "   $DUMP_FILE"
  read -rp "Tapez 'RESTORE' en majuscules pour confirmer : " ans
  [ "$ans" = "RESTORE" ] || { echo "Abandon."; exit 1; }
fi

# ---- Vérification intégrité ----
echo "Vérification intégrité…"
gunzip -t "$DUMP_FILE" || { echo "Dump corrompu"; exit 2; }

# ---- Drop & recreate DB ----
echo "Suppression de la base $DB_NAME…"
docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
  --project-name "$COMPOSE_PROJECT" \
  exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);"

echo "Recréation…"
docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
  --project-name "$COMPOSE_PROJECT" \
  exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# ---- Restauration ----
echo "Restauration en cours (peut prendre plusieurs minutes)…"
gunzip -c "$DUMP_FILE" | docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
  --project-name "$COMPOSE_PROJECT" \
  exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d "$DB_NAME"

# ---- Vérifications post-restauration ----
echo ""
echo "Vérification post-restauration :"
docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
  --project-name "$COMPOSE_PROJECT" \
  exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d "$DB_NAME" \
  -c "SELECT count(*) AS travelers FROM travelers_traveler;"

echo ""
echo "✅ Restauration terminée. Pensez à :"
echo "   1. Redémarrer le container web (Django) pour vider les caches"
echo "   2. Re-runner les migrations si la version a changé"
echo "      docker compose -f $COMPOSE_FILE_BASE -f $COMPOSE_FILE_PROD exec web python manage.py migrate"
echo "   3. Vérifier que les clés Ed25519 et VAPID existent toujours dans le volume keys_data"
