"""
Moteur de formulaires dynamiques.

Permet de configurer sans redéploiement un formulaire d'enquête par maladie :
- DynamicForm (versionné par maladie)
  - FormSection (sections ordonnées)
    - FormField (champs, types variés, validations)
      - FieldOption (options select/radio/checkbox)
      - FieldCondition (logique conditionnelle : afficher si X==Y)

À la soumission : FormSubmission + FormAnswer (un par champ).

Pour le module Ebola : on dispose à la fois d'un modèle "fort" (apps.ebola)
qui structure les champs essentiels en colonnes Django (pour reporting/index),
ET d'un FormSubmission lié (pour la souplesse / évolutions).
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.models import BaseModel
from apps.diseases.models import Disease


class FieldType(models.TextChoices):
    TEXT = "text", _("Texte court")
    TEXTAREA = "textarea", _("Texte long")
    NUMBER = "number", _("Nombre")
    INTEGER = "integer", _("Entier")
    PHONE = "phone", _("Téléphone")
    EMAIL = "email", _("Email")
    DATE = "date", _("Date")
    DATETIME = "datetime", _("Date & heure")
    BOOLEAN = "boolean", _("Oui/Non")
    SELECT = "select", _("Liste déroulante")
    MULTISELECT = "multiselect", _("Liste à choix multiples")
    RADIO = "radio", _("Boutons radio")
    CHECKBOX = "checkbox", _("Cases à cocher")
    GEOLOCATION = "geolocation", _("Géolocalisation (lat,lng)")
    QR_SCAN = "qr_scan", _("Scan QR code")
    IMAGE = "image", _("Image (upload)")
    FILE = "file", _("Fichier (upload)")
    SIGNATURE = "signature", _("Signature")
    COUNTRY = "country", _("Pays (ISO-2)")
    YES_NO_UNKNOWN = "yes_no_unknown", _("Oui / Non / Ne sait pas")


class DynamicForm(BaseModel):
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="forms")
    code = models.SlugField(max_length=80)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False, help_text=_("Formulaire principal de la maladie."))

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Formulaire dynamique")
        verbose_name_plural = _("Formulaires dynamiques")
        constraints = [
            models.UniqueConstraint(fields=["disease", "code", "version"], name="uniq_form_version"),
        ]
        ordering = ["disease", "code", "-version"]

    def __str__(self) -> str:
        return f"{self.disease.code}:{self.code} v{self.version}"


class FormSection(BaseModel):
    form = models.ForeignKey(DynamicForm, on_delete=models.CASCADE, related_name="sections")
    code = models.SlugField(max_length=80)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = _("Section de formulaire")
        verbose_name_plural = _("Sections de formulaire")
        constraints = [
            models.UniqueConstraint(fields=["form", "code"], name="uniq_section_per_form"),
        ]
        ordering = ["order", "id"]


class FormField(BaseModel):
    section = models.ForeignKey(FormSection, on_delete=models.CASCADE, related_name="fields")
    code = models.SlugField(max_length=80)
    label = models.CharField(max_length=250)
    help_text = models.CharField(max_length=300, blank=True)
    type = models.CharField(max_length=30, choices=FieldType.choices)
    is_required = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    # Validation
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    regex = models.CharField(max_length=255, blank=True)
    default_value = models.CharField(max_length=255, blank=True)
    placeholder = models.CharField(max_length=200, blank=True)

    # Scoring (poids dans le moteur de scoring si la valeur "active" le critère)
    risk_weight = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = _("Champ de formulaire")
        verbose_name_plural = _("Champs de formulaire")
        constraints = [
            models.UniqueConstraint(fields=["section", "code"], name="uniq_field_per_section"),
        ]
        ordering = ["order", "id"]


class FieldOption(BaseModel):
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name="options")
    value = models.CharField(max_length=120)
    label = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)
    triggers_risk = models.BooleanField(
        default=False, help_text=_("Si cochée et sélectionnée, contribue au score de risque.")
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Option de champ")
        verbose_name_plural = _("Options de champ")
        constraints = [
            models.UniqueConstraint(fields=["field", "value"], name="uniq_option_per_field"),
        ]
        ordering = ["order", "id"]


class FieldCondition(BaseModel):
    """Condition logique : afficher/cacher un champ selon la valeur d'un autre."""

    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name="conditions")
    depends_on = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name="dependents")
    OPERATORS = (
        ("eq", "="), ("ne", "!="), ("gt", ">"), ("lt", "<"),
        ("contains", "contains"), ("in", "in"),
    )
    operator = models.CharField(max_length=20, choices=OPERATORS)
    expected_value = models.CharField(max_length=255)
    action = models.CharField(
        max_length=20,
        choices=(("show", "show"), ("hide", "hide"), ("require", "require")),
        default="show",
    )


# ---------------------------------------------------------------------------
# Soumissions
# ---------------------------------------------------------------------------
class FormSubmission(BaseModel):
    form = models.ForeignKey(DynamicForm, on_delete=models.PROTECT, related_name="submissions")
    traveler = models.ForeignKey(
        "travelers.Traveler", null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions"
    )
    submitted_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    # Indexation rapide pour requêtes / export
    indexed_data = models.JSONField(default=dict, blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Soumission de formulaire")
        verbose_name_plural = _("Soumissions de formulaire")
        indexes = [
            models.Index(fields=["form", "is_complete"]),
            models.Index(fields=["traveler"]),
        ]


class FormAnswer(BaseModel):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="answers")
    field = models.ForeignKey(FormField, on_delete=models.PROTECT, related_name="answers")
    value_text = models.TextField(blank=True)
    value_number = models.FloatField(null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    value_options = models.JSONField(default=list, blank=True)
    value_file = models.FileField(upload_to="form_uploads/", null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Réponse à un champ")
        verbose_name_plural = _("Réponses aux champs")
        constraints = [
            models.UniqueConstraint(fields=["submission", "field"], name="uniq_answer_per_field"),
        ]

    def clean(self):
        # Validation dynamique selon le type
        t = self.field.type
        if t in {FieldType.NUMBER, FieldType.INTEGER}:
            if self.value_number is None:
                raise ValidationError({"value_number": "Valeur numérique requise."})
            if self.field.min_value is not None and self.value_number < self.field.min_value:
                raise ValidationError("Valeur inférieure au minimum.")
            if self.field.max_value is not None and self.value_number > self.field.max_value:
                raise ValidationError("Valeur supérieure au maximum.")
