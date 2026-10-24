"""Anti-doublon des inscriptions publiques (formulaire web et adaptateur mobile).

Le client rejoue le POST après un timeout, une coupure réseau ou une erreur
502/503/504 (`apiPostWithRetry`), et le voyageur peut resoumettre son brouillon
après une coupure : le serveur a pu valider la fiche entre-temps. Deux
protections, appliquées dans la transaction d'inscription :

1. Clé d'idempotence (en-tête `Idempotency-Key`, une par fiche, réutilisée par
   les retries) réservée en base avant la création : une requête concurrente
   portant la même clé attend la première, puis renvoie sa fiche.
2. Même pièce d'identité + même date d'arrivée + même contact (téléphone ou
   e-mail) : la fiche existante est renvoyée. Le contact est exigé pour ne
   jamais remettre le pass d'un tiers à qui ne connaît que son passeport.
   Un verrou consultatif PostgreSQL sérialise cette vérification.

Aucune fiche existante n'est modifiée, fusionnée ni supprimée.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.models import Value
from django.db.models.functions import Replace, Upper
from rest_framework.exceptions import ParseError

from apps.travelers.models import Traveler

from .models import PublicRegistrationKey

_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
# Séparateurs saisis librement dans un numéro de pièce (« PA 123-456 » = « PA123456 »).
_DOC_SEPARATORS = (" ", "-", ".", "/")


class InvalidIdempotencyKeyError(ParseError):
    """En-tête malformé : réponse 400 via le gestionnaire d'exceptions DRF."""


def idempotency_key(request) -> str:
    """Clé fournie par le client ('' si absente) ; InvalidIdempotencyKeyError si malformée."""
    key = request.META.get("HTTP_IDEMPOTENCY_KEY", "").strip()
    if key and not _KEY_RE.match(key):
        raise InvalidIdempotencyKeyError(
            "En-tête Idempotency-Key invalide (16 à 128 caractères : lettres, chiffres, - ou _)."
        )
    return key


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def traveler_for_key(key: str) -> Traveler | None:
    """Fiche déjà enregistrée sous cette clé (transaction validée)."""
    if not key:
        return None
    return Traveler.objects.filter(registration_keys__digest=_digest(key)).first()


def claim_key(key: str) -> PublicRegistrationKey | None:
    """Réserve la clé dans la transaction courante.

    Si une autre transaction l'a déjà réservée, PostgreSQL attend son issue :
    validée → None (sa fiche est à renvoyer) ; annulée → la réservation réussit.
    """
    try:
        with transaction.atomic():
            return PublicRegistrationKey.objects.create(digest=_digest(key))
    except IntegrityError:
        return None


def bind_key(claim: PublicRegistrationKey | None, traveler: Traveler) -> None:
    if claim is not None:
        claim.traveler = traveler
        claim.save(update_fields=["traveler"])


def normalize_document(value) -> str:
    doc = str(value or "").strip().upper()
    for sep in _DOC_SEPARATORS:
        doc = doc.replace(sep, "")
    return doc


def normalized_document_expr():
    """Équivalent SQL de `normalize_document` sur `Traveler.id_document_number`."""
    expr = Upper("id_document_number")
    for sep in _DOC_SEPARATORS:
        expr = Replace(expr, Value(sep), Value(""))
    return expr


def normalize_phone(value) -> str:
    from apps.notifications.services.router import PhoneValidationError, normalize_phone_number

    if not value:
        return ""
    try:
        return normalize_phone_number(str(value))
    except PhoneValidationError:
        return ""


def lock_identity(identite: dict, arrival: date | None) -> None:
    """Sérialise, jusqu'à la fin de la transaction, les inscriptions d'une même
    pièce d'identité pour une même date d'arrivée."""
    doc = normalize_document(identite.get("id_document_number"))
    if not doc or arrival is None or connection.vendor != "postgresql":
        return
    seed = f"public_registration:{doc}:{arrival.isoformat()}".encode()
    lock_id = int.from_bytes(hashlib.sha256(seed).digest()[:8], "big", signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])


def existing_registration(identite: dict, arrival: date | None) -> Traveler | None:
    """Fiche déjà délivrée pour la même pièce, la même arrivée et le même contact."""
    doc = normalize_document(identite.get("id_document_number"))
    phone = normalize_phone(identite.get("phone_mobile"))
    email = str(identite.get("email") or "").strip().lower()
    if not doc or arrival is None or not (phone or email):
        return None
    candidates = (
        Traveler.objects.filter(arrival_date=arrival, health_passes__isnull=False)
        .annotate(normalized_doc=normalized_document_expr())
        .filter(normalized_doc=doc)
        .distinct()
        .order_by("created_at")
    )
    for traveler in candidates:
        if phone and normalize_phone(traveler.phone_mobile) == phone:
            return traveler
        if email and traveler.email.strip().lower() == email:
            return traveler
    return None
