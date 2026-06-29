"""Module `medical` — fondation du suivi sanitaire complet d'un voyageur.

Cette app porte les concepts qui dépassent la simple `QuarantineRecord` :
  - protocole de suivi configurable par maladie (DiseaseFollowupProtocol)
  - signalement détaillé de symptômes (MedicalSymptomReport)
  - prélèvements biologiques (MedicalSample)
  - analyses laboratoire (LabAnalysis)
  - classification épidémiologique du cas (CaseClassification)
  - journal d'actions de suivi (FollowUpAction)

Toute la chaîne médicale s'appuie sur les modèles `quarantine` existants
(QuarantineRecord = followup_case, DailyCheck = followup_day) pour ne pas
dupliquer la donnée — voir le README de l'app pour la cartographie complète.
"""
