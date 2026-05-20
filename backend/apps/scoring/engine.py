"""
Engine de scoring extensible.

Chaque maladie peut enregistrer un scorer en l'enregistrant via le décorateur
`@register_scorer("EBOLA")`. Le scorer reçoit une "enquête" et retourne (score, level).

Permet de :
- découpler le moteur d'évaluation du modèle de données par maladie ;
- ajouter facilement Mpox, Covid-19, Choléra, etc. sans modifier le cœur.
"""
from __future__ import annotations

from typing import Callable

ScorerFn = Callable[[object], tuple[int, str]]

_SCORERS: dict[str, ScorerFn] = {}


def register_scorer(disease_code: str) -> Callable[[ScorerFn], ScorerFn]:
    def wrap(fn: ScorerFn) -> ScorerFn:
        _SCORERS[disease_code.upper()] = fn
        return fn
    return wrap


def get_scorer(disease_code: str) -> ScorerFn | None:
    return _SCORERS.get(disease_code.upper())


def list_scorers() -> list[str]:
    return sorted(_SCORERS.keys())


# Enregistrement des scorers connus (importés tardivement pour éviter les cycles)
def autoload_default_scorers() -> None:
    try:
        from apps.ebola.services import compute_ebola_risk_score

        register_scorer("EBOLA")(compute_ebola_risk_score)
    except Exception:  # pragma: no cover - chargement défensif
        pass
