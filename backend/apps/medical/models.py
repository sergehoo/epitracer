"""Modèles fondation du suivi sanitaire complet (Phase 9A).

Ces modèles complètent ceux d'`apps.quarantine` (QuarantineRecord, DailyCheck,
FollowUpVisit) qui servent respectivement de FollowUpCase et de FollowUpDay.

Cartographie :
  - DiseaseFollowupProtocol  : protocole configurable par maladie
  - MedicalSymptomReport     : symptôme déclaré (vs. has_symptoms boolean)
  - MedicalSample            : prélèvement biologique
  - LabAnalysis              : analyse labo sur un prélèvement
  - CaseClassification       : classification épidémiologique versionnée
  - FollowUpAction           : log audit de toutes les actions du suivi

Toutes les FK transverses utilisent `on_delete=PROTECT` pour les références
métier (impossible de perdre un résultat labo qui est encore lié à un cas)
et `SET_NULL` pour les utilisateurs (un agent peut quitter le service sans
faire disparaître l'historique).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


# ---------------------------------------------------------------------------
# 1) DiseaseFollowupProtocol
# ---------------------------------------------------------------------------


class DiseaseFollowupProtocol(BaseModel):
    """Protocole de suivi configurable par maladie.

    Un seul protocole par maladie (`OneToOneField`). Permet d'évoluer les
    règles (durée, symptômes critiques, escalade, géoloc obligatoire…) sans
    redéployer le code — on lit la conf au moment de l'évaluation.
    """

    disease = models.OneToOneField(
        "diseases.Disease",
        on_delete=models.CASCADE,
        related_name="followup_protocol",
        verbose_name=_("Maladie"),
    )
    duration_days = models.PositiveSmallIntegerField(
        _("Durée du suivi (jours)"), default=21,
    )
    daily_checkin_required = models.BooleanField(
        _("Check-in quotidien obligatoire"), default=True,
    )
    daily_checkin_recommended = models.BooleanField(
        _("Check-in quotidien recommandé"), default=False,
    )

    # Listes de symptômes (codes machine, ex. "fever", "bleeding") — la
    # source de vérité des libellés reste apps.diseases.Symptom mais on
    # garde une copie ici pour limiter les jointures à l'exécution.
    critical_symptoms = models.JSONField(
        _("Symptômes critiques"), default=list, blank=True,
        help_text=_("Codes machine qui déclenchent une escalade immédiate."),
    )
    monitored_symptoms = models.JSONField(
        _("Symptômes surveillés"), default=list, blank=True,
    )

    # Règles métier (JSON volontairement libre pour évolutivité). Voir
    # les commentaires inline dans le seed pour la grammaire attendue.
    sample_required_rules = models.JSONField(
        _("Règles prélèvement"), default=dict, blank=True,
    )
    lab_analysis_required_rules = models.JSONField(
        _("Règles analyse labo"), default=dict, blank=True,
    )
    escalation_rules = models.JSONField(
        _("Règles d'escalade"), default=dict, blank=True,
    )
    closure_rules = models.JSONField(
        _("Règles de clôture"), default=dict, blank=True,
    )
    notification_schedule = models.JSONField(
        _("Planning de notifications"), default=dict, blank=True,
    )
    field_visit_rules = models.JSONField(
        _("Règles de visite terrain"), default=dict, blank=True,
    )

    # Géoloc — Option 3 (RGPD-safe) : pas de tracking caché, mais
    # alerte si la géoloc consentie n'a pas remonté de ping depuis X h.
    require_geolocation = models.BooleanField(
        _("Géolocalisation requise"), default=True,
    )
    geolocation_alert_after_hours = models.PositiveSmallIntegerField(
        _("Alerte géoloc après (heures)"), default=24,
    )

    is_active = models.BooleanField(_("Actif"), default=True, db_index=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Protocole de suivi")
        verbose_name_plural = _("Protocoles de suivi")

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"Protocole {self.disease.code} ({self.duration_days}j)"


# ---------------------------------------------------------------------------
# 2) MedicalSymptomReport
# ---------------------------------------------------------------------------


class SymptomSeverity(models.TextChoices):
    MILD = "mild", _("Légère")
    MODERATE = "moderate", _("Modérée")
    SEVERE = "severe", _("Sévère")
    CRITICAL = "critical", _("Critique")


class SymptomSource(models.TextChoices):
    CHECKIN = "checkin", _("Check-in")
    VISIT = "visit", _("Visite terrain")
    CALL = "call", _("Appel")
    ADMIN = "admin", _("Saisie admin")


class MedicalSymptomReport(BaseModel):
    """Signalement détaillé de symptôme.

    Distinct du booléen `DailyCheck.has_symptoms` — ce modèle permet de
    déclarer plusieurs symptômes par jour, avec sévérité, source, agent
    déclarant, etc. Le lien `followup_day` reste optionnel pour permettre
    une déclaration hors check-in (visite terrain, appel téléphonique).
    """

    followup_case = models.ForeignKey(
        "quarantine.QuarantineRecord",
        on_delete=models.CASCADE,
        related_name="symptom_reports",
        verbose_name=_("Cas de suivi"),
    )
    followup_day = models.ForeignKey(
        "quarantine.DailyCheck",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="symptom_reports",
        verbose_name=_("Jour de suivi"),
    )
    symptom_code = models.CharField(_("Code symptôme"), max_length=40, db_index=True)
    symptom_label = models.CharField(_("Libellé"), max_length=120)
    severity = models.CharField(
        _("Sévérité"), max_length=20,
        choices=SymptomSeverity.choices,
        default=SymptomSeverity.MILD,
        db_index=True,
    )
    onset_date = models.DateField(_("Date d'apparition"), db_index=True)
    reported_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="symptom_reports_recorded",
        verbose_name=_("Saisi par"),
    )
    reported_by_traveler = models.BooleanField(
        _("Déclaré par le voyageur"), default=False,
    )
    source = models.CharField(
        _("Source"), max_length=20,
        choices=SymptomSource.choices,
        default=SymptomSource.CHECKIN,
        db_index=True,
    )
    notes = models.TextField(_("Notes"), blank=True)
    is_critical = models.BooleanField(
        _("Critique"), default=False, db_index=True,
        help_text=_("True si symptom_code ∈ protocol.critical_symptoms."),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Signalement de symptôme")
        verbose_name_plural = _("Signalements de symptômes")
        indexes = [
            models.Index(fields=["followup_case", "-onset_date"]),
            models.Index(fields=["is_critical", "-created_at"]),
        ]
        ordering = ["-onset_date", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        flag = "!" if self.is_critical else "·"
        return f"{flag} {self.symptom_code} ({self.severity}) — {self.onset_date}"


# ---------------------------------------------------------------------------
# 3) MedicalSample
# ---------------------------------------------------------------------------


class SampleType(models.TextChoices):
    BLOOD = "blood", _("Sang")
    SALIVA = "saliva", _("Salive")
    NASOPHARYNGEAL = "nasopharyngeal", _("Naso-pharyngé")
    URINE = "urine", _("Urine")
    STOOL = "stool", _("Selles")
    OTHER = "other", _("Autre")


class SampleTransportStatus(models.TextChoices):
    REQUESTED = "requested", _("Demandé")
    SCHEDULED = "scheduled", _("Programmé")
    COLLECTED = "collected", _("Effectué")
    IN_TRANSIT = "in_transit", _("En transit")
    RECEIVED = "received", _("Reçu labo")
    REJECTED = "rejected", _("Rejeté")
    CANCELLED = "cancelled", _("Annulé")


class MedicalSample(BaseModel):
    """Prélèvement biologique effectué dans le cadre d'un suivi.

    Le code `sample_code` est unique (ex : "EBO-2026-0001") pour permettre
    une traçabilité physique : étiquette → labo → résultat.
    """

    followup_case = models.ForeignKey(
        "quarantine.QuarantineRecord",
        on_delete=models.PROTECT,  # ne jamais perdre la trace d'un prélèvement
        related_name="samples",
        verbose_name=_("Cas de suivi"),
    )
    followup_day = models.ForeignKey(
        "quarantine.DailyCheck",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="samples",
        verbose_name=_("Jour de suivi"),
    )
    sample_code = models.CharField(
        _("Code prélèvement"), max_length=40, unique=True, db_index=True,
    )
    sample_type = models.CharField(
        _("Type"), max_length=20,
        choices=SampleType.choices,
        default=SampleType.BLOOD,
    )
    collected_at = models.DateTimeField(_("Prélevé le"), null=True, blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="samples_collected",
        verbose_name=_("Préleveur"),
    )
    collection_location = models.CharField(
        _("Lieu de prélèvement"), max_length=200, blank=True,
    )
    transport_conditions = models.TextField(
        _("Conditions de transport"), blank=True,
    )
    # `destination_lab` libre pour démarrer — une FK vers un modèle `Lab`
    # sera ajoutée en 9B/9C une fois les laboratoires modélisés.
    destination_lab = models.CharField(
        _("Laboratoire destinataire"), max_length=200, blank=True,
    )
    transport_status = models.CharField(
        _("Statut transport"), max_length=20,
        choices=SampleTransportStatus.choices,
        default=SampleTransportStatus.REQUESTED,
        db_index=True,
    )
    transport_departed_at = models.DateTimeField(
        _("Départ transport"), null=True, blank=True,
    )
    received_at = models.DateTimeField(
        _("Reçu au labo"), null=True, blank=True,
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Prélèvement médical")
        verbose_name_plural = _("Prélèvements médicaux")
        indexes = [
            models.Index(fields=["followup_case", "-created_at"]),
            models.Index(fields=["transport_status", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"Sample {self.sample_code} ({self.sample_type}/{self.transport_status})"


# ---------------------------------------------------------------------------
# 4) LabAnalysis
# ---------------------------------------------------------------------------


class LabAnalysisStatus(models.TextChoices):
    PENDING = "pending", _("En attente")
    RECEIVED = "received", _("Reçu")
    IN_ANALYSIS = "in_analysis", _("En analyse")
    RESULT_AVAILABLE = "result_available", _("Résultat disponible")
    VALIDATED = "validated", _("Validé")
    COMMUNICATED = "communicated", _("Communiqué")
    REJECTED = "rejected", _("Rejeté")


class LabAnalysisResult(models.TextChoices):
    EMPTY = "", _("—")
    NEGATIVE = "negative", _("Négatif")
    POSITIVE = "positive", _("Positif")
    INDETERMINATE = "indeterminate", _("Indéterminé")
    RETEST = "retest", _("À refaire")


class LabAnalysis(BaseModel):
    """Analyse de laboratoire effectuée sur un MedicalSample.

    Un même prélèvement peut donner lieu à plusieurs analyses (ex : PCR
    puis sérologie). Chaque analyse a son propre cycle de vie
    (`status` + `result`) et peut être validée par un cadre INHP.
    """

    sample = models.ForeignKey(
        MedicalSample,
        on_delete=models.PROTECT,
        related_name="analyses",
        verbose_name=_("Prélèvement"),
    )
    lab_name = models.CharField(_("Laboratoire"), max_length=200)
    test_type = models.CharField(_("Type d'analyse"), max_length=80)
    status = models.CharField(
        _("Statut"), max_length=24,
        choices=LabAnalysisStatus.choices,
        default=LabAnalysisStatus.PENDING,
        db_index=True,
    )
    result = models.CharField(
        _("Résultat"), max_length=20,
        choices=LabAnalysisResult.choices,
        default=LabAnalysisResult.EMPTY,
        blank=True,
        db_index=True,
    )
    received_at = models.DateTimeField(_("Reçu le"), null=True, blank=True)
    analyzed_at = models.DateTimeField(_("Analysé le"), null=True, blank=True)
    validated_at = models.DateTimeField(_("Validé le"), null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="lab_results_validated",
        verbose_name=_("Validé par"),
    )
    result_file = models.FileField(
        _("Fichier résultat"),
        upload_to="lab/",
        null=True, blank=True,
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Analyse de laboratoire")
        verbose_name_plural = _("Analyses de laboratoire")
        indexes = [
            models.Index(fields=["sample", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.test_type} · {self.lab_name} → {self.status}/{self.result or '—'}"


# ---------------------------------------------------------------------------
# 5) CaseClassification
# ---------------------------------------------------------------------------


class CaseClassificationCode(models.TextChoices):
    NOT_SUSPECT = "not_suspect", _("Non suspect")
    UNDER_SURVEILLANCE = "under_surveillance", _("Sous surveillance")
    SUSPECT = "suspect", _("Cas suspect")
    PROBABLE = "probable", _("Cas probable")
    CONFIRMED = "confirmed", _("Cas confirmé")
    EXCLUDED = "excluded", _("Cas exclu")
    RECOVERED = "recovered", _("Rétabli")
    CLOSED = "closed", _("Clôturé")


class CaseClassification(BaseModel):
    """Classification épidémiologique du cas — versionnée.

    Une nouvelle ligne par changement de classification. La ligne courante
    est marquée `is_current=True`, les anciennes sont conservées pour audit.
    Le service `update_case_classification` (Phase 9B) garantit qu'il n'y
    a qu'une ligne `is_current=True` par cas.
    """

    followup_case = models.ForeignKey(
        "quarantine.QuarantineRecord",
        on_delete=models.CASCADE,
        related_name="classifications",
        verbose_name=_("Cas de suivi"),
    )
    classification = models.CharField(
        _("Classification"), max_length=30,
        choices=CaseClassificationCode.choices,
        db_index=True,
    )
    reason = models.TextField(_("Motif"), blank=True)
    classified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="case_classifications",
        verbose_name=_("Classé par"),
    )
    classified_at = models.DateTimeField(_("Classé le"), auto_now_add=True)
    is_current = models.BooleanField(
        _("Classification active"), default=True, db_index=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Classification de cas")
        verbose_name_plural = _("Classifications de cas")
        indexes = [
            models.Index(fields=["followup_case", "is_current"]),
            models.Index(fields=["classification", "-classified_at"]),
        ]
        ordering = ["-classified_at"]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        flag = "*" if self.is_current else "·"
        return f"{flag} {self.classification} — case {self.followup_case_id}"


# ---------------------------------------------------------------------------
# 6) FollowUpAction
# ---------------------------------------------------------------------------


class FollowUpActionType(models.TextChoices):
    CONTACTED = "contacted", _("Contacté")
    NOTIFICATION_SENT = "notification_sent", _("Notification envoyée")
    CALL_SCHEDULED = "call_scheduled", _("Appel programmé")
    VISIT_SCHEDULED = "visit_scheduled", _("Visite programmée")
    SYMPTOM_DECLARED = "symptom_declared", _("Symptôme déclaré")
    SAMPLE_REQUESTED = "sample_requested", _("Prélèvement demandé")
    SAMPLE_COLLECTED = "sample_collected", _("Prélèvement effectué")
    SENT_TO_LAB = "sent_to_lab", _("Envoyé au labo")
    LAB_RESULT_ADDED = "lab_result_added", _("Résultat ajouté")
    ALERT_CREATED = "alert_created", _("Alerte créée")
    ESCALATED = "escalated", _("Escaladé")
    DAY_CLOSED = "day_closed", _("Journée clôturée")
    CASE_CLASSIFIED = "case_classified", _("Classification mise à jour")
    MEDICAL_ORIENTATION = "medical_orientation", _("Orientation médicale")
    FOLLOWUP_CLOSED = "followup_closed", _("Suivi clôturé")


class FollowUpActionStatus(models.TextChoices):
    PLANNED = "planned", _("Planifiée")
    IN_PROGRESS = "in_progress", _("En cours")
    COMPLETED = "completed", _("Effectuée")
    CANCELLED = "cancelled", _("Annulée")


class FollowUpAction(BaseModel):
    """Log de toutes les actions menées dans le cadre du suivi.

    Sert à la fois d'audit (qui a fait quoi quand) et de timeline UI.
    Le champ `metadata` permet de stocker des références opaques (id de
    prélèvement, code alerte, etc.) sans créer un FK par cas d'usage.
    """

    followup_case = models.ForeignKey(
        "quarantine.QuarantineRecord",
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("Cas de suivi"),
    )
    followup_day = models.ForeignKey(
        "quarantine.DailyCheck",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="actions",
        verbose_name=_("Jour de suivi"),
    )
    action_type = models.CharField(
        _("Type d'action"), max_length=40,
        choices=FollowUpActionType.choices,
        db_index=True,
    )
    title = models.CharField(_("Titre"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="followup_actions",
        verbose_name=_("Effectué par"),
    )
    performed_at = models.DateTimeField(
        _("Effectué le"), auto_now_add=True, db_index=True,
    )
    status = models.CharField(
        _("Statut"), max_length=20,
        choices=FollowUpActionStatus.choices,
        default=FollowUpActionStatus.COMPLETED,
        db_index=True,
    )
    metadata = models.JSONField(
        _("Métadonnées"), default=dict, blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Action de suivi")
        verbose_name_plural = _("Actions de suivi")
        indexes = [
            models.Index(fields=["followup_case", "-performed_at"]),
            models.Index(fields=["action_type", "-performed_at"]),
        ]
        ordering = ["-performed_at"]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.action_type} · {self.title[:48]}"
