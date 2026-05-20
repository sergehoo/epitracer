"""Modèles de scoring génériques (réutilisables pour toute maladie)."""
# Volontairement aucun modèle DB ici : le scoring Ebola est colocalisé avec
# l'enquête (`apps.ebola.services.compute_ebola_risk_score`).
# Cet emplacement existe pour héberger les futurs scorers pluggables
# (par maladie : Mpox, Choléra, etc.) sans pollution de l'enquête.
