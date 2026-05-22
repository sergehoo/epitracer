"""
Tâches Celery du module core — opérations transverses non-métier.

Pour le moment :
- `run_postgres_backup` : exécute le script de backup PostgreSQL et
  enregistre le résultat (succès, taille, durée).
- `rotate_old_audit_logs` : nettoyage périodique des très vieux logs
  d'audit (> 5 ans) pour éviter l'inflation indéfinie de la table.

Le scheduling effectif est défini dans `config/celery.py`.
"""
from __future__ import annotations

import logging
import os
import subprocess
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, name="core.run_postgres_backup",
    autoretry_for=(subprocess.CalledProcessError,),
    retry_backoff=True, max_retries=2,
    time_limit=60 * 30,  # 30 minutes max (kill au-delà)
)
def run_postgres_backup(self) -> dict:
    """Lance le script `scripts/backup_postgres.sh` depuis le worker.

    Pré-requis :
    - le worker doit avoir le socket Docker monté pour pouvoir invoquer
      `docker compose exec db pg_dump` ;
    - OU bien le worker tourne en privilégié avec accès direct à la DB
      (préférable : lancer depuis l'hôte via cron, voir scripts/).

    Pour un déploiement standard avec Celery worker dans un container,
    cette tâche se contente d'appeler `pg_dump` via le client psycopg
    en se connectant directement à la DB. Pas besoin de Docker socket.
    """
    from django.conf import settings
    import gzip

    backup_dir = Path(os.environ.get("BACKUP_DIR", "/backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    dump_path = backup_dir / f"epitrace-{timestamp}.sql.gz"

    # Parse DATABASE_URL pour récupérer les credentials
    db = settings.DATABASES["default"]
    pg_env = {
        "PGHOST": db["HOST"] or "db",
        "PGPORT": str(db["PORT"] or 5432),
        "PGUSER": db["USER"],
        "PGPASSWORD": db["PASSWORD"],
        "PGDATABASE": db["NAME"],
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    }

    started = timezone.now()
    logger.info("Backup PostgreSQL démarré → %s", dump_path)

    try:
        # pg_dump → stdout, on pipe dans gzip
        proc = subprocess.Popen(
            ["pg_dump", "--no-owner", "--no-acl"],
            env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        with gzip.open(dump_path, "wb", compresslevel=9) as gz:
            assert proc.stdout is not None
            for chunk in iter(lambda: proc.stdout.read(64 * 1024), b""):
                gz.write(chunk)
        rc = proc.wait()
        stderr = (proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else "")
        if rc != 0:
            dump_path.unlink(missing_ok=True)
            raise subprocess.CalledProcessError(rc, "pg_dump", stderr=stderr)
    except FileNotFoundError as exc:
        logger.error("pg_dump introuvable dans le container worker — ajouter postgresql-client")
        raise self.retry(exc=exc, countdown=60)

    size = dump_path.stat().st_size
    duration = (timezone.now() - started).total_seconds()

    if size < 1024:
        dump_path.unlink(missing_ok=True)
        logger.error("Backup trop petit (%d bytes) — base vide ?", size)
        return {"ok": False, "reason": "too_small", "size": size}

    # Rotation : supprime les dumps > 30 jours
    retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
    cutoff = timezone.now() - timedelta(days=retention_days)
    purged = 0
    for old in backup_dir.glob("epitrace-*.sql.gz"):
        mtime = timezone.datetime.fromtimestamp(old.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            old.unlink(missing_ok=True)
            purged += 1

    logger.info("Backup OK — size=%d, duration=%.1fs, purged=%d", size, duration, purged)
    return {
        "ok": True,
        "path": str(dump_path),
        "size": size,
        "duration_seconds": duration,
        "purged_old": purged,
    }


@shared_task(name="core.rotate_old_audit_logs")
def rotate_old_audit_logs(years: int = 5) -> dict:
    """Supprime les AuditLog plus vieux que `years` ans pour éviter
    l'inflation de la table. Les logs critiques (consultations PII)
    sont conservés via DataAccessLog dans companion.
    """
    try:
        from apps.audit.models import AuditLog
    except ImportError:
        return {"ok": False, "reason": "no_audit_model"}

    cutoff = timezone.now() - timedelta(days=365 * years)
    n, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Rotated %d audit logs older than %d years", n, years)
    return {"ok": True, "deleted": n}
