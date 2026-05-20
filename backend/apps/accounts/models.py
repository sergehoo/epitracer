"""
Modèles d'identité et de contrôle d'accès.

Hiérarchie de rôles (RBAC granulaire) :

    NATIONAL_ADMIN  - super admin national
    MINISTRY        - cadres du Ministère de la Santé
    INHP            - Institut National d'Hygiène Publique
    DISTRICT        - direction d'un district sanitaire
    ENTRY_POINT     - responsable d'un point d'entrée (aéroport, port, frontière)
    BORDER_AGENT    - agent à la frontière qui enregistre les voyageurs
    FIELD_AGENT     - agent terrain (suivi domicile, quarantaine)
    LABORATORY      - personnel laboratoire (résultats biologiques)
    OBSERVER        - observateur (lecture seule sur dashboards)
    TRAVELER        - voyageur (accès limité à ses propres données)

Un User peut avoir plusieurs rôles (RoleAssignment), éventuellement avec un
scope organisationnel (rattachement à une Organization ou un EntryPoint).
"""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.models import BaseModel, TimestampedModel


# ---------------------------------------------------------------------------
# Énumérations de rôles
# ---------------------------------------------------------------------------
class RoleCode(models.TextChoices):
    NATIONAL_ADMIN = "NATIONAL_ADMIN", _("Super Admin National")
    MINISTRY = "MINISTRY", _("Ministère de la Santé")
    INHP = "INHP", _("INHP")
    DISTRICT = "DISTRICT", _("District Sanitaire")
    ENTRY_POINT = "ENTRY_POINT", _("Responsable Point d'Entrée")
    BORDER_AGENT = "BORDER_AGENT", _("Agent Frontière")
    FIELD_AGENT = "FIELD_AGENT", _("Agent Terrain")
    LABORATORY = "LABORATORY", _("Laboratoire")
    OBSERVER = "OBSERVER", _("Observateur")
    TRAVELER = "TRAVELER", _("Voyageur")


class OrganizationType(models.TextChoices):
    MINISTRY = "MINISTRY", _("Ministère")
    INHP = "INHP", _("INHP")
    DISTRICT = "DISTRICT", _("District Sanitaire")
    ENTRY_POINT = "ENTRY_POINT", _("Point d'Entrée")
    LABORATORY = "LABORATORY", _("Laboratoire")
    OTHER = "OTHER", _("Autre")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email)
        username = extra.pop("username", None) or email
        user = self.model(email=email, username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Le superuser doit avoir is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True.")
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Utilisateur EpidemiTracker (identifié par email)."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    email = models.EmailField(_("email"), unique=True, db_index=True)
    phone = models.CharField(_("téléphone"), max_length=32, blank=True, db_index=True)
    job_title = models.CharField(_("fonction"), max_length=120, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # MFA
    mfa_enabled = models.BooleanField(default=False)
    mfa_enforced = models.BooleanField(default=False, help_text=_("Imposer la MFA à la prochaine connexion."))

    # Statut
    is_locked = models.BooleanField(default=False, help_text=_("Verrouillé pour raison de sécurité."))
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_expires_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "is_locked"]),
        ]

    def __str__(self) -> str:
        return f"{self.email}"

    # --- Helpers RBAC --------------------------------------------------
    def role_codes(self) -> list[str]:
        """Retourne la liste des codes de rôles actifs assignés à l'utilisateur."""
        return list(
            self.role_assignments.filter(is_active=True)
            .values_list("role__code", flat=True)
            .distinct()
        )

    def has_role(self, *codes: str) -> bool:
        my = set(self.role_codes())
        return bool(my & set(codes))

    @property
    def display_name(self) -> str:
        full = self.get_full_name()
        return full or self.email


# ---------------------------------------------------------------------------
# Organization (Ministère, INHP, district, point d'entrée, labo)
# ---------------------------------------------------------------------------
class Organization(BaseModel):
    name = models.CharField(max_length=200, db_index=True)
    code = models.SlugField(max_length=60, unique=True)
    type = models.CharField(max_length=30, choices=OrganizationType.choices, db_index=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=255, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Organisation")
        verbose_name_plural = _("Organisations")
        indexes = [models.Index(fields=["type", "name"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


# ---------------------------------------------------------------------------
# Rôles & assignations
# ---------------------------------------------------------------------------
class Role(TimestampedModel):
    code = models.CharField(max_length=40, choices=RoleCode.choices, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True, help_text=_("Rôle prédéfini non supprimable."))
    permissions = models.ManyToManyField(
        "auth.Permission", blank=True, related_name="epidemi_roles"
    )

    class Meta:
        verbose_name = _("Rôle")
        verbose_name_plural = _("Rôles")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class RoleAssignment(TimestampedModel):
    """Assignation d'un rôle à un utilisateur, optionnellement scopée à une organisation."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name="role_assignments"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    granted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="granted_roles"
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Assignation de rôle")
        verbose_name_plural = _("Assignations de rôles")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "organization"],
                name="uniq_role_assignment_per_org",
            ),
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user.email} → {self.role.code} ({self.organization or 'global'})"


# ---------------------------------------------------------------------------
# Sessions / connexions / appareils
# ---------------------------------------------------------------------------
class LoginEvent(TimestampedModel):
    """Trace de chaque tentative de connexion (réussie ou échouée)."""

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="login_events"
    )
    email_attempted = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.CharField(max_length=400, blank=True)
    success = models.BooleanField(default=False, db_index=True)
    failure_reason = models.CharField(max_length=120, blank=True)
    mfa_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Évènement de connexion")
        verbose_name_plural = _("Évènements de connexion")
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["email_attempted", "success"]),
        ]


class TrustedDevice(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trusted_devices")
    label = models.CharField(max_length=120)
    device_id = models.CharField(max_length=128, unique=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Appareil de confiance")
        verbose_name_plural = _("Appareils de confiance")
