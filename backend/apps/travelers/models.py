"""Voyageur, historique des déplacements, lieu de confinement.

Champs strictement alignés sur la fiche officielle INHP "FICHE PASSAGER EBOLA RDC 2026"
(MINISTÈRE DE LA SANTÉ - INHP - République de Côte d'Ivoire).
"""
from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.models import BaseModel
from apps.core.utils import short_id


class Gender(models.TextChoices):
    MALE = "M", _("Masculin")
    FEMALE = "F", _("Féminin")


class AgeUnit(models.TextChoices):
    YEARS = "years", _("Ans")
    MONTHS = "months", _("Mois")


class TransportMode(models.TextChoices):
    PLANE = "plane", _("Avion")
    BOAT = "boat", _("Bateau")
    CAR = "car", _("Voiture")
    BUS = "bus", _("Bus")
    TRAIN = "train", _("Train")
    FOOT = "foot", _("À pied")
    OTHER = "other", _("Autre")


class IDDocumentType(models.TextChoices):
    PASSPORT = "passport", _("Passeport")
    CNI = "cni", _("CNI")
    DRIVER_LICENSE = "driver_license", _("Permis de conduire")
    RESIDENCE_PERMIT = "residence", _("Titre de séjour")
    OTHER = "other", _("Autre")


class Traveler(BaseModel):
    """Voyageur enregistré à un point d'entrée — fidèle au formulaire INHP."""

    public_id = models.CharField(max_length=24, unique=True, editable=False, db_index=True)

    # -------------------------------------------------------------------
    # Section 1 : Informations sur le voyage
    # -------------------------------------------------------------------
    arrival_date = models.DateField(_("Date d'arrivée"), null=True, blank=True, db_index=True)
    arrival_time = models.TimeField(_("Heure d'arrivée"), null=True, blank=True)
    transport_mode = models.CharField(
        _("Moyen de transport"), max_length=20, choices=TransportMode.choices, blank=True
    )
    flight_or_voyage_number = models.CharField(
        _("N° de vol / moyen de transport"), max_length=60, blank=True, db_index=True
    )
    seat_number = models.CharField(_("N° de siège"), max_length=20, blank=True)
    entry_point = models.ForeignKey(
        "geo.EntryPoint", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="arrivals", verbose_name=_("Point d'entrée"),
    )

    # -------------------------------------------------------------------
    # Section 2 : Identité et contacts du passager
    # -------------------------------------------------------------------
    last_name = models.CharField(_("Nom de famille"), max_length=120, db_index=True)
    first_name = models.CharField(_("Prénoms"), max_length=120)
    middle_name = models.CharField(_("Second prénom"), max_length=120, blank=True)
    age = models.PositiveSmallIntegerField(_("Âge"), null=True, blank=True)
    age_unit = models.CharField(
        _("Unité d'âge"), max_length=10, choices=AgeUnit.choices, default=AgeUnit.YEARS
    )
    date_of_birth = models.DateField(_("Date de naissance"), null=True, blank=True)
    gender = models.CharField(_("Sexe"), max_length=2, choices=Gender.choices, blank=True)
    profession = models.CharField(_("Profession"), max_length=160, blank=True)

    # Document d'identité (formulaire INHP demande "N° Passeport")
    id_document_type = models.CharField(
        _("Type pièce d'identité"), max_length=20,
        choices=IDDocumentType.choices, default=IDDocumentType.PASSPORT,
    )
    id_document_number = models.CharField(_("N° Passeport / pièce"), max_length=60, db_index=True)
    id_document_country = models.ForeignKey(
        "geo.Country", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="id_documents_issued",
        verbose_name=_("Pays émetteur"),
    )
    nationality = models.ForeignKey(
        "geo.Country", null=True, blank=True, on_delete=models.SET_NULL, related_name="nationals",
        verbose_name=_("Nationalité"),
    )

    # Contacts (formulaire INHP)
    phone_mobile = models.CharField(_("Téléphone portable"), max_length=32, blank=True, db_index=True)
    email = models.EmailField(_("Adresse e-mail"), blank=True, db_index=True)
    postal_address = models.CharField(_("Adresse postale"), max_length=300, blank=True)

    # Conservé pour compatibilité — alias de phone_mobile
    @property
    def phone(self) -> str:
        return self.phone_mobile

    # -------------------------------------------------------------------
    # Section 4 : Adresse de résidence et confinement en Côte d'Ivoire
    # -------------------------------------------------------------------
    confinement_city = models.CharField(_("Ville (CI)"), max_length=120, blank=True)
    confinement_commune = models.CharField(_("Commune (CI)"), max_length=120, blank=True)
    confinement_neighborhood = models.CharField(_("Quartier (CI)"), max_length=160, blank=True)
    confinement_street_number = models.CharField(_("N° de rue"), max_length=40, blank=True)
    confinement_lot = models.CharField(_("N° de lot"), max_length=40, blank=True)
    confinement_hotel = models.CharField(_("Hôtel / lieu d'hébergement"), max_length=200, blank=True)
    confinement_room_number = models.CharField(_("N° de chambre"), max_length=40, blank=True)
    emergency_phone_ci = models.CharField(
        _("Téléphone d'urgence obligatoire en CI"), max_length=32, blank=True,
    )
    confinement_address = models.CharField(
        _("Adresse de confinement consolidée"), max_length=300, blank=True,
        help_text=_("Champ calculé pour exports et affichage."),
    )
    confinement_location = gis_models.PointField(
        _("Géolocalisation du confinement"), srid=4326, null=True, blank=True, geography=True,
    )

    # -------------------------------------------------------------------
    # Lien optionnel à un compte utilisateur (espace voyageur)
    # -------------------------------------------------------------------
    user = models.OneToOneField(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="traveler_profile",
    )

    # -------------------------------------------------------------------
    # Statut sanitaire courant (dénormalisé pour requêtes rapides)
    # -------------------------------------------------------------------
    current_health_status = models.CharField(
        max_length=20,
        choices=(
            ("cleared", _("Autorisé")),
            ("monitoring", _("Sous surveillance")),
            ("quarantine", _("En quarantaine")),
            ("suspect", _("Cas suspect")),
            ("confirmed", _("Cas confirmé")),
            ("recovered", _("Rétabli")),
            ("deceased", _("Décédé")),
        ),
        default="monitoring",
        db_index=True,
    )

    # Consentement & signature (Section 7 du formulaire)
    consented_data_processing = models.BooleanField(
        _("Certification sur l'honneur"), default=False,
        help_text=_("Je certifie sur l'honneur l'exactitude des renseignements."),
    )
    signed_at = models.DateTimeField(_("Date de signature"), null=True, blank=True)
    signed_place = models.CharField(_("Fait à"), max_length=120, blank=True)
    consent_signature = models.ImageField(upload_to="signatures/", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Voyageur")
        verbose_name_plural = _("Voyageurs")
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["arrival_date", "entry_point"]),
            models.Index(fields=["current_health_status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = short_id("TRV", length=10)
        # Construire l'adresse consolidée pour exports/affichage
        parts = [
            self.confinement_hotel,
            self.confinement_neighborhood,
            self.confinement_commune,
            self.confinement_city,
        ]
        self.confinement_address = ", ".join([p for p in parts if p])
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.public_id} - {self.last_name.upper()} {self.first_name}"

    @property
    def full_name(self) -> str:
        return " ".join(p for p in [self.first_name, self.middle_name, self.last_name] if p)


class TravelHistoryEntry(BaseModel):
    """Étape d'un déplacement antérieur (pays visité, transit, autre).

    Couvre la Section 3 du formulaire :
    - Pays de provenance + ville + adresse + hôtel/N° chambre + durée
    - Pays de transit + ville + adresse + hôtel/N° chambre + durée
    - Autres pays visités les 3 dernières semaines (avec dates de visite)
    """

    class Role(models.TextChoices):
        ORIGIN = "origin", _("Pays de provenance")
        TRANSIT = "transit", _("Pays de transit")
        VISITED = "visited", _("Autre pays visité")

    traveler = models.ForeignKey(Traveler, on_delete=models.CASCADE, related_name="travel_history")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VISITED)
    country = models.ForeignKey("geo.Country", on_delete=models.PROTECT)
    city = models.CharField(max_length=120, blank=True)
    residence_address = models.CharField(max_length=300, blank=True)
    hotel = models.CharField(max_length=200, blank=True)
    room_number = models.CharField(max_length=40, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    departure_date = models.DateField(null=True, blank=True)
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_text = models.CharField(max_length=120, blank=True, help_text=_("Durée libre saisie."))
    notes = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Étape de voyage")
        verbose_name_plural = _("Historique des déplacements")
        ordering = ["-arrival_date", "-id"]
        indexes = [models.Index(fields=["role", "country"])]


class CompanionLink(BaseModel):
    """Lien entre voyageurs voyageant ensemble (utile en contact-tracing)."""

    traveler = models.ForeignKey(Traveler, on_delete=models.CASCADE, related_name="companions")
    companion = models.ForeignKey(Traveler, on_delete=models.CASCADE, related_name="companion_of")
    relationship = models.CharField(max_length=60, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Compagnon de voyage")
        verbose_name_plural = _("Compagnons de voyage")
        constraints = [
            models.UniqueConstraint(fields=["traveler", "companion"], name="uniq_companion_link"),
        ]
