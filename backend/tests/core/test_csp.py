"""Tests CSP — chantier #213-1.

Vérifie que :
  - django-csp est dans INSTALLED_APPS / MIDDLEWARE
  - les directives critiques sont définies au bon niveau (frame-ancestors,
    default-src, object-src 'none' notamment)

On ne teste pas l'injection effective du header sur une vue (cela
nécessiterait un client + un endpoint sans throttle); le smoke test
ci-dessous valide que la config est cohérente — pas que le middleware
émet le header (couvert par django-csp en upstream).
"""
from __future__ import annotations

from django.conf import settings


def test_csp_middleware_installed():
    assert "csp.middleware.CSPMiddleware" in settings.MIDDLEWARE


def test_csp_app_installed():
    assert "csp" in settings.INSTALLED_APPS


def test_csp_directives_minimal():
    # Anti-clickjacking — frame-ancestors 'none'
    assert getattr(settings, "CSP_FRAME_ANCESTORS", None) == ("'none'",)
    # default-src 'self'
    assert getattr(settings, "CSP_DEFAULT_SRC", None) == ("'self'",)
    # object-src bloqué
    assert getattr(settings, "CSP_OBJECT_SRC", None) == ("'none'",)
    # base-uri restreint
    assert getattr(settings, "CSP_BASE_URI", None) == ("'self'",)


def test_csp_includes_nonce_in_script_src():
    assert "script-src" in getattr(settings, "CSP_INCLUDE_NONCE_IN", ())


def test_csp_connect_src_includes_wss():
    connect = getattr(settings, "CSP_CONNECT_SRC", ())
    assert any("wss://" in s for s in connect), connect
