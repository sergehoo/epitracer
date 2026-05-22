"""
Modèles du module Companion — accompagnement voyageur (PWA, push, géoloc).

Cette app gère tout ce qui touche au suivi NON-INVASIF du voyageur pendant
sa période d'accompagnement sanitaire (21 jours pour Ebola) :

- consentements explicites (géolocalisation, notifications push, partage
  de données médicales) avec versionnement et trace d'audit ;
- abonnements Web Push (VAPID) pour rappels quotidiens ;
- pings de localisation collectés UNIQUEMENT après consentement explicite,
  au moment d'une action volontaire (check-in, demande d'aide) ;
- journalisation de tout accès aux données sensibles (RGPD-like).

Les check-ins quotidiens eux-mêmes sont stockés dans
`apps.quarantine.DailyCheck` (déjà existant) ; ce module ne fait que
collecter les métadonnées (push, géoloc, consentement) qui entourent le
check-in et déclencher les alertes via `apps.surveillance.HealthAlert`
existant.

Aucune collecte n'est faite sans `PrivacyConsent.granted = True` pour le
scope correspondant. Les retraits de consentement sont versionnés et
historisés (jamais d'overwrite, jamais de suppression physique).
"""
from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


# ============================================================================
#                          PRIVACY CONSENT
# ============================================================================


class ConsentScope(models.TextChoices):
    """Périmètre d'un consentement.

    Chaque scope est consenti SÉPARÉMENT (granularité fine), pour respecter
    le principe RGPD de finalité spécifique. Un voyageur peut accepter les
    rappels push mais refuser le partage de position, par exemple.
    """

    GEOLOCATION = "geolocation", _("Partage de la position géographique")
    PUSH_NOTIFICATIONS = "push", _("Notifications de rappel sanitaire")
    HEALTH_FOLLOWUP = "health_followup", _("Suivi médical pendant 21 jours")
    DATA_PROCESSING = "data_processing", _("Traitement général des données")


class PrivacyConsent(BaseModel):
    """Consentement explicite et versionné d'un voyageur pour un scope donné.

    Modèle append-only : on ne modifie JAMAIS un consentement existant.
    Si l'utilisateur change d'avis, on crée une nouvelle ligne avec
    `granted=False` et `revoked_at` rempli. Cela garantit un audit
    complet conforme aux obligations légales (loi 2013-450 sur la
    protection des données personnelles en CI).
    """

    traveler = models.ForeignKey(
        "travelers.Traveler",
        on_delete=models.CASCADE,
        related_name="privacy_consents",
        verbose_name=_("Voyageur"),
    )
    scope = models.CharField(
        _("Périmètre"), max_length=32, choices=ConsentScope.choices, db_index=True,
    )
    granted = models.BooleanField(
        _("Consentement accordé"), default=False, db_index=True,
        help_text=_("True = l'utilisateur a explicitement accepté ce scope."),
    )
    # Version du texte de politique de confidentialité au moment du
    # consentement. Permet de retrouver exactement à QUOI le voyageur a
    # consenti (utile en cas de litige ou de mise à jour de politique).
    consent_version = models.CharField(
        _("Version politique"), max_length=20, default="v1",
        help_text=_("Ex : 'v1.0-2026-05'."),
    )
    consent_text_excerpt = models.TextField(
        _("Extrait du texte consenti"), blank=True,
        help_text=_("Snapshot du texte exact présenté à l'utilisateur."),
    )
    # Contexte technique au moment du consentement (audit)
    ip_address = models.GenericIPAddressField(_("Adresse IP"), null=True, blank=True)
    user_agent = models.CharField(_("User-Agent"), max_length=300, blank=True)
    granted_at = models.DateTimeField(_("Date de consentement"), default=timezone.now, db_index=True)
    revoked_at = models.DateTimeField(_("Date de retrait"), null=True, blank=True)
    revocation_reason = models.CharField(_("Motif retrait"), max_length=200, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Consentement de confidentialité")
        verbose_name_plural = _("Consentements de confidentialité")
        ordering = ["-granted_at"]
        indexes = [
            models.Index(fields=["traveler", "scope", "-granted_at"]),
        ]

    def __str__(self) -> str:
        state = "✓" if self.granted else "✗"
        return f"{state} {self.traveler.public_id} · {self.scope} · {self.consent_version}"


# ============================================================================
#                          PUSH SUBSCRIPTION (Web Push, VAPID)
# ============================================================================


class PushSubscriptionDevice(models.TextChoices):
    MOBILE = "mobile", _("Mobile")
    DESKTOP = "desktop", _("Bureau")
    TABLET = "tablet", _("Tablette")
    UNKNOWN = "unknown", _("Inconnu")


class PushSubscription(BaseModel):
    """Abonnement Web Push standard W3C (différent de FCM/APNS).

    Stocke les 3 éléments cryptographiques retournés par
    `pushManager.subscribe()` côté navigateur : `endpoint`, `p256dh`, `auth`.
    Le serveur utilisera `pywebpush` pour envoyer des notifications signées
    VAPID à cet endpoint.

    Un même voyageur peut avoir plusieurs subscriptions (mobile + desktop).
    """

    traveler = models.ForeignKey(
        "travelers.Traveler",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name=_("Voyageur"),
    )
    # `endpoint` est l'URL unique fournie par le navigateur (Mozilla,
    # Chrome, Safari). On l'unique-constraint pour éviter les doublons.
    endpoint = models.URLField(_("Endpoint navigateur"), max_length=500, unique=True)
    p256dh = models.CharField(_("Clé publique P-256"), max_length=200)
    auth = models.CharField(_("Secret d'authentification"), max_length=100)
    # Métadonnées non-sensibles
    user_agent = models.CharField(_("User-Agent"), max_length=300, blank=True)
    device_type = models.CharField(
        _("Type d'appareil"), max_length=10,
        choices=PushSubscriptionDevice.choices,
        default=PushSubscriptionDevice.UNKNOWN,
    )
    locale = models.CharField(_("Langue navigateur"), max_length=10, blank=True)
    is_active = models.BooleanField(_("Actif"), default=True, db_index=True)
    last_used_at = models.DateTimeField(_("Dernière utilisation"), null=True, blank=True)
    failure_count = models.PositiveIntegerField(
        _("Échecs consécutifs"), default=0,
        help_text=_("Désactivé automatiquement après 5 échecs."),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Abonnement push")
        verbose_name_plural = _("Abonnements push")
        indexes = [
            models.Index(fields=["traveler", "is_active"]),
        ]

    def mark_failure(self, error: str = "") -> None:
        """Incrémente le compteur d'échec et désactive si seuil atteint."""
        self.failure_count += 1
        if self.failure_count >= 5:
            self.is_active = False
        self.save(update_fields=["failure_count", "is_active", "updated_at"])

    def mark_success(self) -> None:
        self.failure_count = 0
        self.last_used_at = timezone.now()
        self.save(update_fields=["failure_count", "last_used_at", "updated_at"])


# ============================================================================
#                          LOCATION PING (géoloc consentie)
# ============================================================================


class LocationEventType(models.TextChoices):
    """Quand/pourquoi la position a été collectée.

    Le champ existe pour distinguer les pings volontaires (l'utilisateur a
    cliqué "Partager ma position") des collectes intégrées (au check-in
    quotidien, qui suppose un consentement précédent).
    """

    DAILY_CHECKIN = "daily_checkin", _("Check-in quotidien")
    SYMPTOM_REPORT = "symptom_report", _("Signalement de symptôme")
    ASSISTANCE_REQUEST = "assistance_request", _("Demande d'assistance")
    MANUAL_SHARE = "manual_share", _("Partage volontaire")
    AGENT_VISIT = "agent_visit", _("Visite d'un agent terrain")


class LocationSource(models.TextChoices):
    PWA = "pwa", _("PWA voyageur")
    AGENT_APP = "agent_app", _("Appli agent terrain")
    ADMIN_ENTRY = "admin_entry", _("Saisie manuelle admin")


class TravelerLocationPing(BaseModel):
    """Une position GPS d'un voyageur à un instant donné.

    GARANTIES PRIVACY :
    - chaque ping référence le `consent_version` qui a été présenté
      au voyageur (audit complet) ;
    - aucun ping n'est créé sans un `PrivacyConsent` actif de scope
      `GEOLOCATION` pour ce voyageur ;
    - les pings sont accessibles uniquement aux rôles autorisés
      (INHP, district, urgence, agent affecté).
    """

    traveler = models.ForeignKey(
        "travelers.Traveler",
        on_delete=models.CASCADE,
        related_name="location_pings",
        verbose_name=_("Voyageur"),
    )
    # Coordonnées WGS84
    latitude = models.DecimalField(_("Latitude"), max_digits=10, decimal_places=7)
    longitude = models.DecimalField(_("Longitude"), max_digits=10, decimal_places=7)
    point = gis_models.PointField(_("Position (PostGIS)"), srid=4326, geography=True, db_index=True)
    # Qualité de la position (Web Geolocation API)
    accuracy_m = models.FloatField(_("Précision (m)"), null=True, blank=True)
    altitude_m = models.FloatField(_("Altitude (m)"), null=True, blank=True)
    speed_mps = models.FloatField(_("Vitesse (m/s)"), null=True, blank=True)
    heading_deg = models.FloatField(_("Direction (°)"), null=True, blank=True)
    # Métadonnées événement
    event_type = models.CharField(
        _("Événement"), max_length=24, choices=LocationEventType.choices,
        default=LocationEventType.DAILY_CHECKIN, db_index=True,
    )
    source = models.CharField(
        _("Source"), max_length=16, choices=LocationSource.choices,
        default=LocationSource.PWA,
    )
    captured_at = models.DateTimeField(_("Capturée le"), default=timezone.now, db_index=True)
    # Audit consentement
    consent_version = models.CharField(_("Version politique"), max_length=20, blank=True)
    device_info = models.CharField(_("Infos appareil"), max_length=200, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Ping de localisation")
        verbose_name_plural = _("Pings de localisation")
        ordering = ["-captured_at"]
        indexes = [
            models.Index(fields=["traveler", "-captured_at"]),
            models.Index(fields=["event_type", "-captured_at"]),
        ]


# ============================================================================
#                          DATA ACCESS LOG (RGPD)
# ============================================================================


class DataAccessLog(BaseModel):
    """Trace de chaque accès à des données sensibles (positions, contacts,
    pièce d'identité). Obligatoire pour répondre à un éventuel droit
    d'accès du voyageur ("qui a consulté mes données ?").

    Append-only — jamais d'UPDATE.
    """

    class Resource(models.TextChoices):
        LOCATION = "location", _("Localisation")
        CONTACT = "contact", _("Coordonnées")
        IDENTITY = "identity", _("Pièce d'identité")
        HEALTH = "health", _("Données de santé")
        FULL_PROFILE = "full_profile", _("Profil complet")

    traveler = models.ForeignKey(
        "travelers.Traveler",
        on_delete=models.CASCADE,
        related_name="access_logs",
        verbose_name=_("Voyageur concerné"),
    )
    accessed_by = models.ForeignKey(
        "accounts.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="data_accesses",
        verbose_name=_("Utilisateur accédant"),
    )
    accessed_by_role = models.CharField(
        _("Rôle au moment de l'accès"), max_length=40, blank=True,
        help_text=_("Snapshot du rôle (immuable même si le rôle change après)."),
    )
    resource = models.CharField(
        _("Ressource"), max_length=20, choices=Resource.choices, db_index=True,
    )
    reason = models.CharField(
        _("Motif"), max_length=200, blank=True,
        help_text=_("Raison opérationnelle (ex: 'Investigation alerte HA-1234')."),
    )
    ip_address = models.GenericIPAddressField(_("Adresse IP"), null=True, blank=True)
    user_agent = models.CharField(_("User-Agent"), max_length=300, blank=True)
    accessed_at = models.DateTimeField(_("Accédé le"), default=timezone.now, db_index=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Journal d'accès aux données")
        verbose_name_plural = _("Journaux d'accès aux données")
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["traveler", "-accessed_at"]),
            models.Index(fields=["resource", "-accessed_at"]),
        ]
