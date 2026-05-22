"""Migration initiale du module Companion.

Crée les 4 tables :
- companion_privacyconsent
- companion_pushsubscription
- companion_travelerlocationping (avec PointField PostGIS)
- companion_dataaccesslog
"""
import uuid

import django.contrib.gis.db.models.fields
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("travelers", "0004_add_whatsapp_and_province"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ---------------- PrivacyConsent ----------------
        migrations.CreateModel(
            name="PrivacyConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="supprimé le")),
                ("scope", models.CharField(choices=[
                    ("geolocation", "Partage de la position géographique"),
                    ("push", "Notifications de rappel sanitaire"),
                    ("health_followup", "Suivi médical pendant 21 jours"),
                    ("data_processing", "Traitement général des données"),
                ], db_index=True, max_length=32, verbose_name="Périmètre")),
                ("granted", models.BooleanField(db_index=True, default=False, verbose_name="Consentement accordé",
                                                help_text="True = l'utilisateur a explicitement accepté ce scope.")),
                ("consent_version", models.CharField(default="v1", max_length=20, verbose_name="Version politique")),
                ("consent_text_excerpt", models.TextField(blank=True, verbose_name="Extrait du texte consenti")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="Adresse IP")),
                ("user_agent", models.CharField(blank=True, max_length=300, verbose_name="User-Agent")),
                ("granted_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now,
                                                    verbose_name="Date de consentement")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="Date de retrait")),
                ("revocation_reason", models.CharField(blank=True, max_length=200, verbose_name="Motif retrait")),
                ("traveler", models.ForeignKey(on_delete=models.CASCADE, related_name="privacy_consents",
                                                to="travelers.traveler", verbose_name="Voyageur")),
            ],
            options={
                "verbose_name": "Consentement de confidentialité",
                "verbose_name_plural": "Consentements de confidentialité",
                "ordering": ["-granted_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="privacyconsent",
            index=models.Index(fields=["traveler", "scope", "-granted_at"],
                               name="companion_p_travele_b6f0e2_idx"),
        ),

        # ---------------- PushSubscription ----------------
        migrations.CreateModel(
            name="PushSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="supprimé le")),
                ("endpoint", models.URLField(max_length=500, unique=True, verbose_name="Endpoint navigateur")),
                ("p256dh", models.CharField(max_length=200, verbose_name="Clé publique P-256")),
                ("auth", models.CharField(max_length=100, verbose_name="Secret d'authentification")),
                ("user_agent", models.CharField(blank=True, max_length=300, verbose_name="User-Agent")),
                ("device_type", models.CharField(choices=[
                    ("mobile", "Mobile"), ("desktop", "Bureau"),
                    ("tablet", "Tablette"), ("unknown", "Inconnu"),
                ], default="unknown", max_length=10, verbose_name="Type d'appareil")),
                ("locale", models.CharField(blank=True, max_length=10, verbose_name="Langue navigateur")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Actif")),
                ("last_used_at", models.DateTimeField(blank=True, null=True, verbose_name="Dernière utilisation")),
                ("failure_count", models.PositiveIntegerField(default=0, verbose_name="Échecs consécutifs",
                                                              help_text="Désactivé automatiquement après 5 échecs.")),
                ("traveler", models.ForeignKey(on_delete=models.CASCADE, related_name="push_subscriptions",
                                                to="travelers.traveler", verbose_name="Voyageur")),
            ],
            options={
                "verbose_name": "Abonnement push",
                "verbose_name_plural": "Abonnements push",
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="pushsubscription",
            index=models.Index(fields=["traveler", "is_active"],
                               name="companion_p_travele_a26b87_idx"),
        ),

        # ---------------- TravelerLocationPing ----------------
        migrations.CreateModel(
            name="TravelerLocationPing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="supprimé le")),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10, verbose_name="Latitude")),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10, verbose_name="Longitude")),
                ("point", django.contrib.gis.db.models.fields.PointField(
                    geography=True, srid=4326, db_index=True, verbose_name="Position (PostGIS)")),
                ("accuracy_m", models.FloatField(blank=True, null=True, verbose_name="Précision (m)")),
                ("altitude_m", models.FloatField(blank=True, null=True, verbose_name="Altitude (m)")),
                ("speed_mps", models.FloatField(blank=True, null=True, verbose_name="Vitesse (m/s)")),
                ("heading_deg", models.FloatField(blank=True, null=True, verbose_name="Direction (°)")),
                ("event_type", models.CharField(choices=[
                    ("daily_checkin", "Check-in quotidien"),
                    ("symptom_report", "Signalement de symptôme"),
                    ("assistance_request", "Demande d'assistance"),
                    ("manual_share", "Partage volontaire"),
                    ("agent_visit", "Visite d'un agent terrain"),
                ], db_index=True, default="daily_checkin", max_length=24, verbose_name="Événement")),
                ("source", models.CharField(choices=[
                    ("pwa", "PWA voyageur"),
                    ("agent_app", "Appli agent terrain"),
                    ("admin_entry", "Saisie manuelle admin"),
                ], default="pwa", max_length=16, verbose_name="Source")),
                ("captured_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now,
                                                     verbose_name="Capturée le")),
                ("consent_version", models.CharField(blank=True, max_length=20, verbose_name="Version politique")),
                ("device_info", models.CharField(blank=True, max_length=200, verbose_name="Infos appareil")),
                ("traveler", models.ForeignKey(on_delete=models.CASCADE, related_name="location_pings",
                                                to="travelers.traveler", verbose_name="Voyageur")),
            ],
            options={
                "verbose_name": "Ping de localisation",
                "verbose_name_plural": "Pings de localisation",
                "ordering": ["-captured_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="travelerlocationping",
            index=models.Index(fields=["traveler", "-captured_at"],
                               name="companion_t_travele_8c91f4_idx"),
        ),
        migrations.AddIndex(
            model_name="travelerlocationping",
            index=models.Index(fields=["event_type", "-captured_at"],
                               name="companion_t_event_t_5dbe2c_idx"),
        ),

        # ---------------- DataAccessLog ----------------
        migrations.CreateModel(
            name="DataAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="supprimé le")),
                ("accessed_by_role", models.CharField(blank=True, max_length=40,
                                                      verbose_name="Rôle au moment de l'accès",
                                                      help_text="Snapshot du rôle (immuable même si le rôle change après).")),
                ("resource", models.CharField(choices=[
                    ("location", "Localisation"),
                    ("contact", "Coordonnées"),
                    ("identity", "Pièce d'identité"),
                    ("health", "Données de santé"),
                    ("full_profile", "Profil complet"),
                ], db_index=True, max_length=20, verbose_name="Ressource")),
                ("reason", models.CharField(blank=True, max_length=200, verbose_name="Motif",
                                            help_text="Raison opérationnelle (ex: 'Investigation alerte HA-1234').")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="Adresse IP")),
                ("user_agent", models.CharField(blank=True, max_length=300, verbose_name="User-Agent")),
                ("accessed_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now,
                                                     verbose_name="Accédé le")),
                ("accessed_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL,
                                                  related_name="data_accesses", to=settings.AUTH_USER_MODEL,
                                                  verbose_name="Utilisateur accédant")),
                ("traveler", models.ForeignKey(on_delete=models.CASCADE, related_name="access_logs",
                                                to="travelers.traveler", verbose_name="Voyageur concerné")),
            ],
            options={
                "verbose_name": "Journal d'accès aux données",
                "verbose_name_plural": "Journaux d'accès aux données",
                "ordering": ["-accessed_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="dataaccesslog",
            index=models.Index(fields=["traveler", "-accessed_at"],
                               name="companion_d_travele_1c3f8a_idx"),
        ),
        migrations.AddIndex(
            model_name="dataaccesslog",
            index=models.Index(fields=["resource", "-accessed_at"],
                               name="companion_d_resourc_2d9b6e_idx"),
        ),
    ]
