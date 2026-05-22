"""Régénère les PDF de tous les Health Pass existants.

Quand on modifie `apps.health_pass.services.render_pass_pdf` (par exemple
pour retirer le bandeau de risque), les fichiers PDF déjà stockés dans
`HealthPass.pdf_file` gardent l'ancien rendu. Cette commande les
ré-écrit avec le template actuel.

Usage :
    python manage.py regen_pass_pdfs               # tous les pass actifs
    python manage.py regen_pass_pdfs --all         # tous, y compris révoqués
    python manage.py regen_pass_pdfs --dry-run     # comptage uniquement
    python manage.py regen_pass_pdfs --public-id TRV-XXX  # un seul pass
"""
from __future__ import annotations

import logging

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.health_pass.crypto import PREFIX, _b64u_encode, sign_payload
from apps.health_pass.models import HealthPass
from apps.health_pass.services import render_pass_pdf
import json

logger = logging.getLogger(__name__)


def _rebuild_token(hp: HealthPass) -> str:
    """Reconstruit le token QR (format EPMS1.<payload>.<signature>).

    1. Si `payload` ET `signature_b64` sont persistés → on rebuild sans
       re-signer, la signature d'origine reste la vérité.
    2. Sinon (pass legacy) → on re-signe avec la clé courante (le QR
       imprimé deviendra invérifiable ; ne concerne que d'anciens pass).
    """
    payload = hp.payload or {}
    signature_b64 = hp.signature_b64 or ""

    if payload and signature_b64:
        # Sérialiser le payload EXACTEMENT comme à l'émission
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return f"{PREFIX}.{_b64u_encode(payload_json)}.{signature_b64}"

    # Fallback legacy
    minimal_payload = {
        "iss": "MSHPCMU-CI",
        "pid": hp.pass_number,
        "tid": hp.traveler.public_id,
        "iat": hp.issued_at.isoformat() if hp.issued_at else None,
        "exp": hp.expires_at.isoformat() if hp.expires_at else None,
    }
    token, sig = sign_payload(minimal_payload)
    hp.payload = minimal_payload
    hp.signature_b64 = sig
    hp.save(update_fields=["payload", "signature_b64"])
    return token


class Command(BaseCommand):
    help = "Régénère les PDF des Health Pass (utile après modification du template)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true",
                            help="Inclure aussi les pass révoqués / expirés.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--public-id", default=None,
                            help="Ne régénérer que le pass d'un voyageur donné.")

    def handle(self, *args, **opts):
        qs = HealthPass.objects.all().select_related("traveler", "disease")
        if not opts["all"]:
            qs = qs.filter(status="active")
        if opts["public_id"]:
            qs = qs.filter(traveler__public_id=opts["public_id"].upper())

        total = qs.count()
        self.stdout.write(f"Pass à traiter : {total}")
        if opts["dry_run"]:
            return

        ok = 0
        ko = 0
        for hp in qs.iterator(chunk_size=50):
            try:
                token = _rebuild_token(hp)
                pdf_bytes = render_pass_pdf(hp, token)
                filename = f"{hp.pass_number}.pdf"
                # Replace l'ancien fichier (save=True écrit en DB)
                hp.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
                ok += 1
                if ok % 10 == 0:
                    self.stdout.write(f"  ✓ {ok}/{total}")
            except Exception as exc:  # noqa: BLE001
                ko += 1
                logger.exception("Échec régénération pour %s", hp.pass_number)
                self.stdout.write(self.style.WARNING(f"  ✗ {hp.pass_number}: {exc}"))

        self.stdout.write(self.style.SUCCESS(
            f"Terminé : {ok} régénérés, {ko} échecs sur {total}."
        ))
