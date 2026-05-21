"""Helpers de branding officiel CI utilisés par les PDFs (pass + fiche INHP).

Charge les 3 logos officiels en cache mémoire :
  - Emblème (armoiries) de la République de Côte d'Ivoire
  - Logo du Ministère MSHPCMU
  - Logo de l'INHP

Les fichiers PNG sont stockés dans backend/static/branding/.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# --- Couleurs République de Côte d'Ivoire / drapeau ----------------------
CI_ORANGE = colors.HexColor("#F77F00")
CI_WHITE = colors.HexColor("#FFFFFF")
CI_GREEN = colors.HexColor("#009B5A")
CI_DARK = colors.HexColor("#064E3B")
CI_GOLD = colors.HexColor("#D4A017")
SLATE_50 = colors.HexColor("#F8FAFC")
SLATE_500 = colors.HexColor("#64748B")
SLATE_900 = colors.HexColor("#0F172A")

# --- Textes officiels (abréviation MSHPCMU) ------------------------------
HEADER_TOP = "RÉPUBLIQUE DE CÔTE D'IVOIRE"
HEADER_MOTTO = "Union • Discipline • Travail"
HEADER_MINISTRY_FULL = (
    "Ministère de la Santé, de l'Hygiène Publique et de la Couverture Maladie Universelle"
)
HEADER_MINISTRY = "MSHPCMU"  # abréviation officielle
HEADER_INHP = "Institut National d'Hygiène Publique (INHP)"
INHP_CONTACT = "Tél : 143     Email : info@destinationci.com"

# --- Fichiers logos officiels (stockés en local) -------------------------
BRAND_DIR = Path(getattr(settings, "BASE_DIR", Path("."))) / "static" / "branding"
LOGO_MSHPCMU = BRAND_DIR / "mshpcmu.png"
LOGO_ARMOIRIE = BRAND_DIR / "armoirie.png"
LOGO_INHP = BRAND_DIR / "inhp.png"


@lru_cache(maxsize=8)
def _load_image(path: str) -> ImageReader | None:
    p = Path(path)
    if p.exists():
        try:
            return ImageReader(str(p))
        except Exception:  # pragma: no cover
            return None
    return None


def get_mshpcmu_logo() -> ImageReader | None:
    return _load_image(str(LOGO_MSHPCMU))


def get_armoirie_logo() -> ImageReader | None:
    return _load_image(str(LOGO_ARMOIRIE))


def get_inhp_logo() -> ImageReader | None:
    return _load_image(str(LOGO_INHP))


def draw_ci_flag_band(c, x: float, y: float, width: float, height: float):
    """Trace le drapeau ivoirien (orange/blanc/vert vertical)."""
    band = width / 3.0
    c.setFillColor(CI_ORANGE); c.rect(x, y, band, height, stroke=0, fill=1)
    c.setFillColor(CI_WHITE);  c.rect(x + band, y, band, height, stroke=0, fill=1)
    c.setFillColor(CI_GREEN);  c.rect(x + 2 * band, y, band, height, stroke=0, fill=1)


def draw_ci_emblem(c, cx: float, cy: float, radius: float):
    """Emblème de secours si l'image des armoiries n'est pas disponible."""
    c.setFillColor(CI_DARK)
    c.circle(cx, cy, radius, stroke=0, fill=1)
    import math
    c.setStrokeColor(CI_ORANGE)
    c.setLineWidth(2)
    for i in range(8):
        ang = i * (math.pi / 4)
        c.line(
            cx + math.cos(ang) * radius * 0.55,
            cy + math.sin(ang) * radius * 0.55,
            cx + math.cos(ang) * radius * 0.92,
            cy + math.sin(ang) * radius * 0.92,
        )
    c.setFillColor(CI_ORANGE)
    c.circle(cx, cy, radius * 0.45, stroke=0, fill=1)
    c.setFillColor(CI_WHITE)
    c.setFont("Helvetica-Bold", radius * 0.55)
    c.drawCentredString(cx, cy - radius * 0.18, "CI")
