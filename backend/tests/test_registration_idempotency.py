"""Inscriptions voyageurs en double (formulaire public et adaptateur mobile).

Cause : `apiPostWithRetry` rejoue le POST après un timeout, une coupure réseau
ou une erreur 502/503/504 alors que le serveur a pu valider la fiche ; le
formulaire invite aussi à resoumettre le brouillon conservé après une coupure.
Le serveur doit donc reconnaître une soumission déjà traitée :
  - même clé d'idempotence (`Idempotency-Key`) → fiche existante renvoyée ;
  - même pièce d'identité + même date d'arrivée + même contact → idem.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.health_pass.models import HealthPass
from apps.travelers.models import Traveler

URL = "/api/v1/ebola/public/register/"
MOBILE_URL = "/api/mobile/forms/ebola_inhp_v1/submissions/"


def _payload(**identite):
    return {
        "voyage": {
            "arrival_date": timezone.localdate().isoformat(),
            "transport_mode": "air",
            "flight_or_voyage_number": "EK000",
            "entry_point_code": "ABJ",
        },
        "identite": {
            "last_name": "KOUASSI",
            "first_name": "Awa",
            "gender": "F",
            "id_document_type": "passport",
            "id_document_number": "PA1234567",
            "phone_mobile": "+61400000001",
            "email": "awa.kouassi@example.org",
            **identite,
        },
        # Pays de provenance obligatoire (code ISO2 connu du référentiel).
        "historique": [{"role": "origin", "country_code": "FR", "city": "Paris"}],
        "confinement": {"city": "Abidjan"},
        "exposure": {},
        "symptoms": {},
        "declaration": {"truthful_declaration": True},
    }


def _post(payload, key: str | None = None, url: str = URL):
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    return APIClient().post(url, payload, format="json", **headers)


@pytest.fixture
def portal(pass_keys, entry_point, ebola_disease):
    """Formulaire public opérationnel : clés de signature, point d'entrée, Ebola actif."""


# ===========================================================================
# 1. Retry après timeout / coupure réseau (même clé)
# ===========================================================================
@pytest.mark.django_db
class TestIdempotencyKey:
    def test_retry_after_timeout_returns_the_same_registration(self, portal):
        key = str(uuid.uuid4())
        first = _post(_payload(), key)
        assert first.status_code == 201, first.data

        # Le client n'a pas reçu la réponse (timeout) : apiPostWithRetry rejoue le POST.
        retry = _post(_payload(), key)

        assert retry.status_code == 200, retry.data
        assert retry.data["already_registered"] is True
        assert retry.data["traveler"]["public_id"] == first.data["traveler"]["public_id"]
        assert retry.data["pass"]["pass_number"] == first.data["pass"]["pass_number"]
        assert Traveler.objects.count() == 1
        assert HealthPass.objects.count() == 1

    def test_replay_does_not_need_a_new_turnstile_token(self, portal, settings):
        """Resoumission du brouillon après expiration du jeton anti-robot (à usage unique)."""
        key = str(uuid.uuid4())
        first = _post(_payload(), key)
        assert first.status_code == 201, first.data

        settings.TURNSTILE = {
            **settings.TURNSTILE, "SECRET_KEY": "secret",
            "PROTECTED_ACTIONS": ["public_registration"],
        }
        retry = _post(_payload(), key)

        assert retry.status_code == 200, retry.data
        assert retry.data["traveler"]["public_id"] == first.data["traveler"]["public_id"]

    def test_new_key_without_identity_match_creates_a_new_registration(self, portal):
        assert _post(_payload(), str(uuid.uuid4())).status_code == 201
        other = _payload(id_document_number="PB7654321", phone_mobile="+61400000002", email="")
        assert _post(other, str(uuid.uuid4())).status_code == 201
        assert Traveler.objects.count() == 2

    @pytest.mark.parametrize("key", ["court", "x" * 129, "clé avec espaces 123456"])
    def test_malformed_key_is_rejected(self, portal, key):
        resp = _post(_payload(), key)
        assert resp.status_code == 400
        assert Traveler.objects.count() == 0

    def test_cors_preflight_allows_the_header(self, settings):
        """Le front (destinationci.com) appelle l'API sur un autre domaine : un en-tête
        refusé au preflight bloquerait toute inscription web."""
        settings.CORS_ALLOWED_ORIGINS = ["https://destinationci.com"]
        resp = APIClient().options(
            URL,
            HTTP_ORIGIN="https://destinationci.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,idempotency-key",
        )
        assert "idempotency-key" in resp["Access-Control-Allow-Headers"]

    def test_mobile_adapter_honours_the_key(self, pass_keys):
        answers = {
            "arrival_date": timezone.localdate().isoformat(),
            "flight_or_voyage_number": "EK000",
            "last_name": "KOUASSI", "first_name": "Awa", "gender": "F",
            "id_document_number": "PA1234567", "phone_mobile": "+61400000001",
            "origin_country": "FR", "origin_city": "Paris", "origin_duration": "10 jours",
            "city": "Abidjan", "truthful": True,
        }
        key = str(uuid.uuid4())
        first = _post({"answers": answers}, key, url=MOBILE_URL)
        assert first.status_code == 201, first.data
        retry = _post({"answers": answers}, key, url=MOBILE_URL)
        assert retry.status_code == 200, retry.data
        assert retry.data["traveler"]["public_id"] == first.data["traveler"]["public_id"]
        assert Traveler.objects.count() == 1


# ===========================================================================
# 2. Même pièce d'identité + même date d'arrivée (sans clé commune)
# ===========================================================================
@pytest.mark.django_db
class TestSameDocumentAndArrival:
    def test_resubmission_with_reformatted_contact_returns_existing(self, portal):
        first = _post(_payload())
        assert first.status_code == 201, first.data

        again = _post(_payload(id_document_number="pa 123-4567", phone_mobile="+61 400 000 001"))

        assert again.status_code == 200, again.data
        assert again.data["already_registered"] is True
        assert again.data["traveler"]["public_id"] == first.data["traveler"]["public_id"]
        assert Traveler.objects.count() == 1

    def test_same_email_is_enough_when_phone_differs(self, portal):
        first = _post(_payload())
        again = _post(_payload(phone_mobile="+61400000999", email="AWA.KOUASSI@example.org"))
        assert again.status_code == 200, again.data
        assert again.data["traveler"]["public_id"] == first.data["traveler"]["public_id"]

    def test_document_alone_never_returns_someone_elses_registration(self, portal):
        """Sans contact commun, on ne renvoie pas la fiche (pass, statut sanitaire) d'un tiers."""
        _post(_payload())
        other = _post(_payload(phone_mobile="+61400000999", email="autre@example.org"))
        assert other.status_code == 201
        assert Traveler.objects.count() == 2

    def test_new_arrival_date_is_a_new_trip(self, portal):
        _post(_payload())
        later = _payload()
        later["voyage"]["arrival_date"] = (timezone.localdate() + timedelta(days=30)).isoformat()
        assert _post(later).status_code == 201
        assert Traveler.objects.count() == 2


# ===========================================================================
# 3. Double soumission concurrente (vraies transactions, une connexion par thread)
# ===========================================================================
@pytest.fixture
def live_db(django_db_setup, django_db_blocker):
    """Autocommit, sans `transaction=True` (son flush effacerait les données de
    référence des migrations en `--reuse-db`) : le test nettoie ce qu'il crée."""
    with django_db_blocker.unblock():
        yield


@pytest.fixture
def slow_pass(monkeypatch):
    """Allonge la transaction d'inscription pour garantir le chevauchement."""
    from apps.ebola import public_views

    original = public_views.issue_pass_for_registration

    def slow(*args, **kwargs):
        time.sleep(0.5)
        return original(*args, **kwargs)

    monkeypatch.setattr(public_views, "issue_pass_for_registration", slow)


def _concurrently(*payloads_and_keys):
    barrier = threading.Barrier(len(payloads_and_keys))
    responses, errors = [None] * len(payloads_and_keys), []

    def worker(i, payload, key):
        try:
            barrier.wait(timeout=10)
            responses[i] = _post(payload, key)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=worker, args=(i, p, k))
        for i, (p, k) in enumerate(payloads_and_keys)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, errors
    return responses


def _purge(document_number: str):
    from apps.audit.models import AuditLog
    from apps.ebola.models import EbolaInvestigation

    travelers = Traveler.all_objects.filter(id_document_number=document_number)
    pks = list(travelers.values_list("pk", flat=True))
    public_ids = list(travelers.values_list("public_id", flat=True))
    investigations = EbolaInvestigation.all_objects.filter(traveler_id__in=pks)
    inv_pks = list(investigations.values_list("pk", flat=True))
    for public_id in public_ids:
        AuditLog.objects.filter(summary__contains=public_id).delete()
    travelers.delete()
    Traveler.history.filter(id__in=pks).delete()
    EbolaInvestigation.history.filter(id__in=inv_pks).delete()


class TestConcurrentDoubleSubmission:
    def test_double_click_with_same_key_creates_one_registration(
        self, live_db, pass_keys, slow_pass,
    ):
        doc = f"CONC{uuid.uuid4().hex[:8].upper()}"
        payload, key = _payload(id_document_number=doc), str(uuid.uuid4())
        try:
            responses = _concurrently((payload, key), (payload, key))

            statuses = sorted(r.status_code for r in responses)
            assert statuses == [200, 201], [r.data for r in responses]
            assert len({r.data["traveler"]["public_id"] for r in responses}) == 1
            assert Traveler.objects.filter(id_document_number=doc).count() == 1
        finally:
            _purge(doc)

    def test_two_tabs_without_shared_key_create_one_registration(
        self, live_db, pass_keys, slow_pass,
    ):
        doc = f"CONC{uuid.uuid4().hex[:8].upper()}"
        payload = _payload(id_document_number=doc)
        try:
            responses = _concurrently((payload, str(uuid.uuid4())), (payload, None))

            statuses = sorted(r.status_code for r in responses)
            assert statuses == [200, 201], [r.data for r in responses]
            assert Traveler.objects.filter(id_document_number=doc).count() == 1
        finally:
            _purge(doc)


# ===========================================================================
# 4. Repérage des doublons déjà en base (lecture seule)
# ===========================================================================
@pytest.mark.django_db
def test_duplicate_report_lists_groups_without_modifying_anything(traveler):
    arrival = timezone.localdate()
    Traveler.objects.filter(pk=traveler.pk).update(arrival_date=arrival)
    twin = Traveler.objects.create(
        first_name="Aïcha", last_name="Diallo", gender="F", arrival_date=arrival,
        id_document_number="p 123-456", phone_mobile="+225 07 08 09 09 11",
    )
    alone = Traveler.objects.create(
        first_name="Yao", last_name="KONAN", gender="M", arrival_date=arrival,
        id_document_number="Z999", phone_mobile="+2250102030405",
    )
    before = Traveler.objects.count()

    out = StringIO()
    call_command("find_duplicate_travelers", stdout=out)

    report = out.getvalue()
    assert traveler.public_id in report and twin.public_id in report
    assert alone.public_id not in report
    assert Traveler.objects.count() == before
