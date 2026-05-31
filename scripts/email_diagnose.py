"""Diagnostic email EpiTrace — détecte la config + tente un envoi live.

Usage en prod :

    docker compose exec web python manage.py shell < scripts/email_diagnose.py

Ce script :
  1. Affiche la config courante (backend, from, clés présentes/absentes).
  2. Vérifie que django-anymail est bien installé.
  3. Pour SendGrid : valide la clé API via un appel HTTP léger.
  4. Tente un envoi à TEST_EMAIL (configurable via TEST_EMAIL env var) en
     passant par toute la chaîne (dispatcher → providers.send_email).
  5. Imprime un verdict clair.

Le script ne modifie rien en DB sauf création d'une Notification email de
test (si l'envoi atteint au moins le dispatcher).
"""
from __future__ import annotations

import os
import sys

from django.conf import settings
from django.core.mail import send_mail


def _section(title: str) -> None:
    print()
    print("=" * 78)
    print(f"  {title}")
    print("=" * 78)


def _show_config() -> dict:
    _section("1. CONFIGURATION EMAIL")
    backend = settings.EMAIL_BACKEND
    from_addr = settings.DEFAULT_FROM_EMAIL
    sendgrid_key = (getattr(settings, "ANYMAIL", {}) or {}).get("SENDGRID_API_KEY", "")
    print(f"  EMAIL_BACKEND      : {backend}")
    print(f"  DEFAULT_FROM_EMAIL : {from_addr}")
    print(f"  SENDGRID_API_KEY   : {'set ('+sendgrid_key[:8]+'…)' if sendgrid_key else 'VIDE'}")
    return {
        "backend": backend,
        "from": from_addr,
        "sendgrid_key": sendgrid_key,
        "is_sendgrid": "sendgrid" in backend.lower(),
        "is_console": "console" in backend.lower(),
        "is_smtp": "smtp" in backend.lower(),
    }


def _check_anymail():
    _section("2. PAQUETS PYTHON")
    try:
        import anymail
        print(f"  django-anymail     : v{getattr(anymail, '__version__', '?')} ✓")
    except ImportError:
        print("  django-anymail     : ❌ NON installé (pip install django-anymail[sendgrid])")
        return False
    try:
        import sendgrid  # noqa: F401
        print("  sendgrid (client)  : ✓")
    except ImportError:
        # On utilise anymail directement via HTTP, sendgrid SDK non requis
        print("  sendgrid SDK       : non installé (OK, anymail utilise httpx/requests)")
    return True


def _validate_sendgrid_key(api_key: str) -> bool:
    _section("3. VALIDATION CLÉ SENDGRID (API call)")
    if not api_key:
        print("  ⚠️  Pas de clé SendGrid configurée — skip.")
        return False
    try:
        import httpx
    except ImportError:
        import urllib.request
        import json
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/scopes",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                print(f"  ✅ Clé VALIDE — scopes : {len(data.get('scopes', []))} permissions")
                return True
        except Exception as exc:
            print(f"  ❌ Clé invalide : {exc}")
            return False

    try:
        r = httpx.get(
            "https://api.sendgrid.com/v3/scopes",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r.status_code == 200:
            scopes = r.json().get("scopes", [])
            print(f"  ✅ Clé VALIDE — {len(scopes)} permissions accordées")
            # Filtre les scopes "mail.send" et "mail.batch"
            mail_send = [s for s in scopes if "mail" in s.lower() and "send" in s.lower()]
            if mail_send:
                print(f"  ✓ Permission mail.send présente : {mail_send[:3]}")
            else:
                print("  ⚠️  Permission `mail.send` non détectée — envoi pourrait échouer.")
            return True
        elif r.status_code == 401:
            print("  ❌ Clé SendGrid REFUSÉE (HTTP 401) — vérifier l'API key dans .env")
            return False
        else:
            print(f"  ❌ HTTP {r.status_code} : {r.text[:200]}")
            return False
    except Exception as exc:
        print(f"  ❌ Réseau : {exc}")
        return False


def _verify_sender_domain(api_key: str, from_addr: str):
    _section("4. VALIDATION EXPÉDITEUR (domaine autorisé SendGrid)")
    if not api_key or not from_addr:
        print("  ⚠️  Clé ou expéditeur manquant — skip.")
        return
    domain = from_addr.split("@")[-1] if "@" in from_addr else ""
    print(f"  Domaine émetteur : {domain}")
    if not domain:
        print("  ❌ DEFAULT_FROM_EMAIL invalide.")
        return
    try:
        import httpx
        r = httpx.get(
            "https://api.sendgrid.com/v3/whitelabel/domains",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  ⚠️  Impossible de lister les domaines whitelabel : HTTP {r.status_code}")
            return
        domains = r.json()
        matched = [d for d in domains if d.get("domain") == domain]
        if matched:
            d = matched[0]
            print(f"  ✅ Domaine `{domain}` enregistré chez SendGrid")
            print(f"     valid       : {d.get('valid')}")
            print(f"     custom_spf  : {d.get('custom_spf')}")
            if not d.get("valid"):
                print("     ⚠️  Domaine PAS encore validé — DNS records à publier")
        else:
            print(f"  ⚠️  Domaine `{domain}` NON enregistré dans SendGrid whitelabel")
            print("     → SendGrid acceptera l'email MAIS Gmail/Outlook iront en spam")
            print("     → Aller dans Settings → Sender Authentication → Authenticate Your Domain")
    except Exception as exc:
        print(f"  ⚠️  Lecture domaines impossible : {exc}")


def _live_test(from_addr: str):
    _section("5. ENVOI LIVE — test direct send_mail()")
    to = os.environ.get("TEST_EMAIL", "")
    if not to:
        print("  ⚠️  Pas de TEST_EMAIL fourni — skip envoi.")
        print("     Pour tester : TEST_EMAIL=ton.email@example.com puis relancer.")
        return False

    print(f"  De      : {from_addr}")
    print(f"  À       : {to}")
    try:
        sent = send_mail(
            subject="[EpiTrace] Test diagnostic email",
            message=(
                "Ceci est un test du canal email EpiTrace.\n\n"
                "Si vous recevez ce message, l'envoi via Django + backend "
                f"`{settings.EMAIL_BACKEND}` fonctionne.\n\n"
                "— EpiTrace / INHP"
            ),
            from_email=None,
            recipient_list=[to],
            fail_silently=False,
        )
        if sent:
            print(f"  ✅ Envoi accepté ({sent} message). Vérifie ta boîte (et SPAMS).")
            return True
        print("  ⚠️  send_mail a renvoyé 0 — backend n'a rien fait.")
        return False
    except Exception as exc:
        print(f"  ❌ ÉCHEC : {exc}")
        return False


def _chain_test(from_addr: str):
    _section("6. CHAÎNE COMPLÈTE — dispatcher.enqueue_notification(channel='email')")
    to = os.environ.get("TEST_EMAIL", "")
    if not to:
        print("  ⚠️  Pas de TEST_EMAIL fourni — skip.")
        return
    try:
        from apps.notifications.services.dispatcher import enqueue_notification
        r = enqueue_notification(
            channel="email",
            recipient=to,
            subject="[EpiTrace] Test chaîne notifications (email)",
            body="Test envoi via le dispatcher EpiTrace (chaîne complète + Celery).",
        )
        print(f"  ok       : {r.ok}")
        print(f"  notif id : {r.notification_id}")
        print(f"  error    : {r.error or '—'}")
        if r.ok:
            print("  → Vérifier dans 30 sec que le worker l'a bien traité (admin Django).")
    except Exception as exc:
        print(f"  ❌ ÉCHEC : {exc}")


def _verdict(cfg: dict, key_valid: bool):
    _section("7. VERDICT")
    if cfg["is_console"]:
        print("  ⚠️  EMAIL_BACKEND est `console` — les emails s'affichent dans les logs")
        print("     Django mais NE SONT PAS envoyés réellement.")
        print("     → En prod : EMAIL_BACKEND=anymail.backends.sendgrid.EmailBackend")
        return
    if cfg["is_sendgrid"]:
        if not cfg["sendgrid_key"]:
            print("  ❌ Backend SendGrid mais clé API VIDE → tous les envois échoueront.")
            print("     → Ajouter ANYMAIL_SENDGRID_API_KEY=SG.xxx dans .env")
            return
        if not key_valid:
            print("  ❌ Clé API SendGrid invalide ou expirée.")
            print("     → Régénérer une clé sur app.sendgrid.com → API Keys")
            return
        print("  ✅ Configuration SendGrid opérationnelle.")
        print("     Pense à : (1) authentifier ton domaine pour éviter le spam,")
        print("     (2) brancher les webhooks events pour le tracking.")
    elif cfg["is_smtp"]:
        print("  ℹ️  Backend SMTP direct — vérifier credentials SMTP dans .env.")
    else:
        print(f"  ❓ Backend `{cfg['backend']}` — non standard, vérifier manuellement.")


def main():
    cfg = _show_config()
    if not _check_anymail():
        return
    key_valid = False
    if cfg["is_sendgrid"]:
        key_valid = _validate_sendgrid_key(cfg["sendgrid_key"])
        if key_valid:
            _verify_sender_domain(cfg["sendgrid_key"], cfg["from"])
    _live_test(cfg["from"])
    _chain_test(cfg["from"])
    _verdict(cfg, key_valid)


main()
