#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Backup PostgreSQL d'EpiTrace.
#
# Lance un pg_dump compressé du container `db`, écrit le résultat sous
#   /backups/epitrace-YYYYMMDD-HHMMSS.sql.gz
# vérifie l'intégrité du fichier (gunzip -t), purge les backups plus
# vieux que BACKUP_RETENTION_DAYS (30 par défaut), et expose des
# métriques Prometheus (textfile collector) sous /var/lib/node_exporter/.
#
# Usage manuel :
#   bash scripts/backup_postgres.sh
#
# Usage cron (host) :
#   0 2 * * *  /home/ubuntu/epitracer/scripts/backup_postgres.sh >> /var/log/epitrace-backup.log 2>&1
#
# Usage Celery beat (in-container) :
#   apps.core.tasks.run_postgres_backup — voir backend/apps/core/tasks.py
# ---------------------------------------------------------------------------
set -euo pipefail

# ---- Découverte du repo + lecture sélective du .env ----
# On ne fait PAS `source .env` car les .env de docker-compose contiennent
# souvent des apostrophes / espaces / accents incompatibles avec bash
# (ex: NATIONAL_ORG_NAME="Ministère de la Santé - Côte d'Ivoire").
# On extrait uniquement les variables dont on a besoin via grep/awk.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$REPO_DIR"

read_env_var() {
  # Récupère une variable depuis .env sans le sourcer.
  # Strip quotes simples/doubles autour de la valeur.
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

# ---- Configuration (override via env) ----
BACKUP_DIR=${BACKUP_DIR:-/backups}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
COMPOSE_FILE_BASE=${COMPOSE_FILE_BASE:-docker-compose.yml}
COMPOSE_FILE_PROD=${COMPOSE_FILE_PROD:-docker-compose.prod.yml}
COMPOSE_PROJECT=${COMPOSE_PROJECT:-$(basename "$REPO_DIR")}
DB_SERVICE=${DB_SERVICE:-db}
# Détection automatique du user/DB depuis l'env du container db si rien
# n'est passé : c'est la vérité de référence (le container a été initialisé
# avec ces credentials au premier docker-compose up).
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
METRICS_DIR=${METRICS_DIR:-/var/lib/node_exporter/textfile_collector}
# Cible distante optionnelle (S3 via aws CLI, ou rsync over SSH)
REMOTE_TARGET=${REMOTE_TARGET:-}   # ex: "s3://epitrace-backups/postgres/" ou "user@host:/srv/backups/"

# ---- Préparation ----
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
DUMP_FILE="$BACKUP_DIR/epitrace-$TIMESTAMP.sql.gz"

log() { printf "[%(%Y-%m-%dT%H:%M:%SZ)T] %s\n" -1 "$*"; }
fail() { log "ERROR: $*"; write_metric 0; exit 1; }

write_metric() {
  # 1 si succès, 0 si échec
  local status=$1
  local size=${2:-0}
  local duration=${3:-0}
  mkdir -p "$METRICS_DIR" 2>/dev/null || true
  if [ -d "$METRICS_DIR" ]; then
    cat > "$METRICS_DIR/epitrace_backup.prom" <<EOF
# HELP epitrace_backup_last_status 1 = success, 0 = failure
# TYPE epitrace_backup_last_status gauge
epitrace_backup_last_status $status
# HELP epitrace_backup_last_timestamp_seconds Unix timestamp of last backup
# TYPE epitrace_backup_last_timestamp_seconds gauge
epitrace_backup_last_timestamp_seconds $(date +%s)
# HELP epitrace_backup_last_size_bytes Size of last successful dump
# TYPE epitrace_backup_last_size_bytes gauge
epitrace_backup_last_size_bytes $size
# HELP epitrace_backup_last_duration_seconds Time taken by last backup
# TYPE epitrace_backup_last_duration_seconds gauge
epitrace_backup_last_duration_seconds $duration
EOF
  fi
}

START_TS=$(date +%s)
log "Démarrage backup → $DUMP_FILE"

# ---- pg_dump dans le container db ----
if ! docker compose -f "$COMPOSE_FILE_BASE" -f "$COMPOSE_FILE_PROD" \
     --project-name "$COMPOSE_PROJECT" \
     exec -T "$DB_SERVICE" \
     pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl \
     | gzip -9 > "$DUMP_FILE"; then
  fail "pg_dump a échoué"
fi

# ---- Vérification intégrité ----
if ! gunzip -t "$DUMP_FILE" 2>/dev/null; then
  rm -f "$DUMP_FILE"
  fail "Fichier de backup corrompu (gunzip -t failed)"
fi

SIZE=$(stat -c%s "$DUMP_FILE" 2>/dev/null || stat -f%z "$DUMP_FILE")
[ "$SIZE" -lt 1024 ] && fail "Backup trop petit ($SIZE bytes) — base probablement vide ?"

# ---- Upload distant (optionnel) ----
if [ -n "$REMOTE_TARGET" ]; then
  log "Upload vers $REMOTE_TARGET"
  case "$REMOTE_TARGET" in
    s3://*) aws s3 cp "$DUMP_FILE" "$REMOTE_TARGET" --quiet || fail "aws s3 cp a échoué" ;;
    *@*:*)  scp -B "$DUMP_FILE" "$REMOTE_TARGET" || fail "scp a échoué" ;;
    *)      log "Format REMOTE_TARGET non reconnu, skip upload" ;;
  esac
fi

# ---- Rotation locale ----
find "$BACKUP_DIR" -maxdepth 1 -name 'epitrace-*.sql.gz' -mtime "+$BACKUP_RETENTION_DAYS" -delete
KEPT=$(find "$BACKUP_DIR" -maxdepth 1 -name 'epitrace-*.sql.gz' | wc -l)

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

log "OK — size=$SIZE bytes, duration=${DURATION}s, kept=$KEPT files locally"
write_metric 1 "$SIZE" "$DURATION"
