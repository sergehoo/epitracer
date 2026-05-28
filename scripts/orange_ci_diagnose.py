"""Script de diagnostic complet Orange CI SMS — sandbox vs production.

Usage en prod :

    docker compose exec web python manage.py shell < scripts/orange_ci_diagnose.py

Ce script :
  1. Affiche la configuration courante (sans exposer les secrets en clair).
  2. Demande un token OAuth et l'analyse (durée, scopes annoncés).
  3. Liste les 5 dernières notifications Orange CI.
  4. Pour chaque notif avec `provider_message_id` (resourceURL), tente :
       - GET deliveryInfos → vérifie si Orange retourne le statut réel
       - Décode le hostname (api.orange.com vs backend.dck.cloud.orange)
  5. Imprime un verdict :
       - "PROD" si deliveryInfos répond 200
       - "SANDBOX SUSPECT" si HTTP 201 sur POST mais 403/404 sur deliveryInfos
       - "AUTRE" si autre comportement

Le script ne modifie RIEN en DB — lecture seule.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote, urlparse

import httpx
from django.conf import settings

from apps.notifications.models import Notification, Provider
from apps.notifications.services.sms_orange_ci import (
    _get_access_token, _get_settings, _mask,
)


def _section(title: str) -> None:
    print()
    print("=" * 78)
    print(f"  {title}")
    print("=" * 78)


def _show_config() -> dict:
    _section("1. CONFIGURATION ORANGE CI")
    cfg = _get_settings()
    print(f"  enabled           : {cfg['enabled']}")
    print(f"  base_url          : {cfg['base_url']}")
    print(f"  token_url         : {cfg['token_url']}")
    print(f"  sender_name       : {cfg['sender_name']!r}")
    print(f"  client_id         : {cfg['client_id'][:6]}…{cfg['client_id'][-4:] if len(cfg['client_id']) > 10 else ''}")
    print(f"  client_secret     : {'(set)' if cfg['client_secret'] else '(VIDE)'}")
    print(f"  callback_url      : {cfg.get('callback_url') or '(non configuré ←)'}")
    print(f"  webhook_token     : {'(set)' if getattr(settings, 'NOTIFICATIONS', {}).get('ORANGE_CI_WEBHOOK_TOKEN') else '(VIDE)'}")
    return cfg


def _get_token(cfg: dict) -> str | None:
    _section("2. TOKEN OAUTH")
    try:
        token = _get_access_token(force_refresh=True)
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ ÉCHEC : {exc}")
        return None

    # Re-fetch le détail brut pour voir scope/expires_in
    try:
        r = httpx.post(
            cfg["token_url"],
            data={"grant_type": "client_credentials"},
            auth=(cfg["client_id"], cfg["client_secret"]),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        data = r.json() if r.status_code == 200 else {}
    except Exception:  # noqa: BLE001
        data = {}

    print(f"  token (truncated) : {token[:24]}…")
    print(f"  expires_in        : {data.get('expires_in', '?')} sec")
    print(f"  token_type        : {data.get('token_type', '?')}")
    print(f"  scope             : {data.get('scope', '(non renvoyé)')}")
    return token


def _list_recent_notifs(limit: int = 5):
    _section(f"3. {limit} DERNIÈRES NOTIFS ORANGE CI")
    qs = (
        Notification.objects
        .filter(provider=Provider.ORANGE_CI)
        .order_by("-created_at")[:limit]
    )
    rows = list(qs)
    for n in rows:
        print(
            f"  #{n.id:4d}  {n.status:10s}  to={_mask(n.normalized_phone):20s}  "
            f"created={n.created_at.strftime('%Y-%m-%d %H:%M')}  "
            f"msg_id={(n.provider_message_id or '')[:60]}"
        )
    if not rows:
        print("  (aucune notification Orange CI en base)")
    return rows


def _probe_delivery_infos(token: str, notifs):
    _section("4. SONDAGE deliveryInfos PAR NOTIF")
    if not notifs:
        print("  (rien à sonder)")
        return []

    verdicts = []
    for n in notifs:
        url = n.provider_message_id or ""
        if not url.startswith("http"):
            print(f"  #{n.id}: skip (provider_message_id non-URL : {url!r})")
            continue

        info_url = url.rstrip("/") + "/deliveryInfos"
        host = urlparse(info_url).hostname or "?"
        print(f"\n  --- Notif #{n.id} ---")
        print(f"  URL  : {info_url}")
        print(f"  Host : {host}")

        try:
            r = httpx.get(
                info_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=15,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Réseau : {exc}")
            verdicts.append(("NETWORK_ERR", n.id, host, str(exc)))
            continue

        ctype = r.headers.get("content-type", "")
        body_preview = r.text[:300].replace("\n", " ")
        print(f"  HTTP {r.status_code}  content-type={ctype}")
        print(f"  Body : {body_preview}")

        if r.status_code == 200 and "json" in ctype:
            try:
                data = r.json()
                # Path standard : deliveryInfoList.deliveryInfo[*].deliveryStatus
                infos = (
                    data.get("deliveryInfoList", {}).get("deliveryInfo", [])
                    or data.get("deliveryInfo", [])
                )
                if isinstance(infos, dict):
                    infos = [infos]
                for di in infos or []:
                    print(
                        f"     → address={di.get('address')}  "
                        f"deliveryStatus={di.get('deliveryStatus')}"
                    )
                verdicts.append(("PROD_OK", n.id, host, "deliveryInfos lisible"))
            except Exception as exc:  # noqa: BLE001
                verdicts.append(("PARSE_ERR", n.id, host, str(exc)))
        elif r.status_code in (401, 403):
            verdicts.append(("SANDBOX_SUSPECT", n.id, host, f"HTTP {r.status_code}"))
        elif r.status_code == 404:
            verdicts.append(("NOT_FOUND", n.id, host, "ressource purgée ou inconnue"))
        else:
            verdicts.append(("OTHER", n.id, host, f"HTTP {r.status_code}"))
    return verdicts


def _verdict(verdicts):
    _section("5. VERDICT")
    if not verdicts:
        print("  Aucun verdict (pas de notif testée).")
        return

    counts = {}
    for code, *_ in verdicts:
        counts[code] = counts.get(code, 0) + 1

    for code, n in counts.items():
        print(f"  {code:18s} : {n}")

    print()
    if counts.get("PROD_OK", 0) > 0:
        print("  ✅ Au moins une notif a un deliveryInfos lisible — l'app fonctionne EN PRODUCTION.")
        print("     → Si des SMS n'arrivent pas, le problème est côté opérateur / whitelist.")
    elif counts.get("SANDBOX_SUSPECT", 0) > 0:
        print("  ⚠️  Toutes les requêtes deliveryInfos retournent 401/403.")
        print("     → Hypothèse FORTE : l'app est en mode SANDBOX/TEST.")
        print("     → Action : contacter Orange Business CI pour passage en PRODUCTION,")
        print("       envoyer client_id + numéros de test + sender INHP.")
    else:
        print("  ❓ Comportement non standard — voir détails ci-dessus.")

    # Vérifie aussi si le callback est configuré
    cfg = _get_settings()
    if not cfg.get("callback_url"):
        print()
        print("  ⚠️  ORANGE_CI_SMS_CALLBACK_URL est VIDE.")
        print("     → Même en prod, Orange ne pourra pas pousser les delivery reports.")
        print("     → Ajouter au .env :")
        print("         ORANGE_CI_SMS_CALLBACK_URL=https://api.veillesanitaire.com/api/v1/notifications/webhooks/orange-ci/sms/status/")
        print("         ORANGE_CI_WEBHOOK_TOKEN=<token aléatoire long>")


def main():
    cfg = _show_config()
    if not (cfg["client_id"] and cfg["client_secret"]):
        print("\n  ❌ Credentials manquants — arrêt.")
        return
    token = _get_token(cfg)
    if not token:
        return
    notifs = _list_recent_notifs(limit=5)
    verdicts = _probe_delivery_infos(token, notifs)
    _verdict(verdicts)


main()
