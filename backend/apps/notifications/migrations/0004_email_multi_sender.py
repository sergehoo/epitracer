"""Migration : système email multi-expéditeur.

Crée SenderProfile, EmailTemplate, EmailLog, PasswordResetToken et seed
les deux profils de base (public / internal).
"""
from django.conf import settings
from django.db import migrations, models


def seed_sender_profiles(apps, schema_editor):
    """Crée les deux profils PUBLIC et INTERNAL avec valeurs par défaut."""
    SenderProfile = apps.get_model("notifications", "SenderProfile")
    SenderProfile.objects.update_or_create(
        code="public",
        defaults={
            "name": "Voyageurs / Grand public",
            "from_address": "infos@destinationci.com",
            "from_name": "Destination CI - Accompagnement Voyageur",
            "reply_to": "infos@destinationci.com",
            "usage_scope": "public_traveler",
            "is_active": True,
        },
    )
    SenderProfile.objects.update_or_create(
        code="internal",
        defaults={
            "name": "INHP / Administration interne",
            "from_address": "inhp@veillesanitaire.com",
            "from_name": "INHP - Veille Sanitaire",
            "reply_to": "inhp@veillesanitaire.com",
            "usage_scope": "internal_admin",
            "is_active": True,
        },
    )


def reverse_seed(apps, schema_editor):
    SenderProfile = apps.get_model("notifications", "SenderProfile")
    SenderProfile.objects.filter(code__in=["public", "internal"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_rename_notif_traveler_created_idx_notificatio_travele_1ecc92_idx_and_more"),
        ("travelers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── SenderProfile ────────────────────────────────────────────────
        migrations.CreateModel(
            name="SenderProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(
                    choices=[("public", "Public — voyageurs (destinationci.com)"),
                             ("internal", "Interne — administration (veillesanitaire.com)")],
                    max_length=40, unique=True, verbose_name="code")),
                ("name", models.CharField(max_length=120, verbose_name="nom interne")),
                ("from_address", models.EmailField(max_length=254, verbose_name="adresse d'expédition")),
                ("from_name", models.CharField(max_length=120, verbose_name="nom affiché")),
                ("reply_to", models.EmailField(blank=True, max_length=254, verbose_name="adresse de réponse (Reply-To)")),
                ("usage_scope", models.CharField(
                    choices=[("public_traveler", "Voyageurs / grand public"),
                             ("internal_admin", "Administration interne")],
                    max_length=20, verbose_name="portée d'usage")),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Profil d'expéditeur email",
                "verbose_name_plural": "Profils d'expéditeur email",
                "ordering": ["code"],
            },
        ),

        # ── EmailTemplate ────────────────────────────────────────────────
        migrations.CreateModel(
            name="EmailTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(db_index=True, max_length=80, unique=True, verbose_name="code unique")),
                ("name", models.CharField(max_length=160, verbose_name="nom")),
                ("email_type", models.CharField(
                    choices=[
                        ("traveler_info", "Information voyageur"),
                        ("traveler_campaign", "Campagne de sensibilisation"),
                        ("health_notification", "Notification sanitaire"),
                        ("followup_reminder", "Rappel de suivi"),
                        ("pass_confirmation", "Confirmation de pass sanitaire"),
                        ("public_assistance", "Assistance publique"),
                        ("traveler_alert", "Alerte voyageur"),
                        ("followup_completed", "Fin de suivi 21 jours"),
                        ("admin_account_created", "Création compte admin/agent"),
                        ("admin_password_reset", "Réinitialisation mot de passe"),
                        ("admin_security_alert", "Alerte sécurité admin"),
                        ("staff_notification", "Notification agent"),
                        ("internal_report", "Rapport interne"),
                        ("mfa_notification", "Notification MFA"),
                        ("user_invitation", "Invitation utilisateur"),
                        ("system_alert", "Alerte système"),
                    ],
                    db_index=True, max_length=40, verbose_name="type d'email")),
                ("subject", models.CharField(max_length=300, verbose_name="sujet")),
                ("body_html", models.TextField(verbose_name="corps HTML")),
                ("body_text", models.TextField(blank=True, verbose_name="corps texte (fallback)")),
                ("variables_schema", models.JSONField(
                    blank=True, default=dict,
                    help_text='Ex: {"full_name": "string", "pass_number": "string"}',
                    verbose_name="variables attendues (JSON Schema light)")),
                ("is_active", models.BooleanField(default=True)),
                ("sender_profile", models.ForeignKey(
                    blank=True, null=True,
                    help_text="Si vide, déterminé automatiquement par email_type.",
                    on_delete=models.deletion.PROTECT,
                    related_name="templates",
                    to="notifications.senderprofile")),
            ],
            options={
                "verbose_name": "Template email",
                "verbose_name_plural": "Templates email",
                "ordering": ["email_type", "code"],
            },
        ),

        # ── EmailLog ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="EmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recipient", models.EmailField(db_index=True, max_length=254, verbose_name="destinataire")),
                ("email_type", models.CharField(
                    choices=[
                        ("traveler_info", "Information voyageur"),
                        ("traveler_campaign", "Campagne de sensibilisation"),
                        ("health_notification", "Notification sanitaire"),
                        ("followup_reminder", "Rappel de suivi"),
                        ("pass_confirmation", "Confirmation de pass sanitaire"),
                        ("public_assistance", "Assistance publique"),
                        ("traveler_alert", "Alerte voyageur"),
                        ("followup_completed", "Fin de suivi 21 jours"),
                        ("admin_account_created", "Création compte admin/agent"),
                        ("admin_password_reset", "Réinitialisation mot de passe"),
                        ("admin_security_alert", "Alerte sécurité admin"),
                        ("staff_notification", "Notification agent"),
                        ("internal_report", "Rapport interne"),
                        ("mfa_notification", "Notification MFA"),
                        ("user_invitation", "Invitation utilisateur"),
                        ("system_alert", "Alerte système"),
                    ],
                    db_index=True, max_length=40, verbose_name="type")),
                ("sender_address", models.EmailField(max_length=254, verbose_name="adresse expéditeur")),
                ("subject", models.CharField(max_length=300, verbose_name="sujet")),
                ("body_html", models.TextField(blank=True, verbose_name="corps HTML envoyé")),
                ("body_text", models.TextField(blank=True, verbose_name="corps texte envoyé")),
                ("status", models.CharField(
                    choices=[
                        ("pending", "En attente"), ("queued", "En file"),
                        ("sent", "Envoyé"), ("delivered", "Délivré"),
                        ("bounced", "Rejeté (bounce)"), ("failed", "Échec"),
                        ("cancelled", "Annulé"), ("opened", "Ouvert"),
                        ("clicked", "Cliqué"),
                    ],
                    db_index=True, default="pending", max_length=20, verbose_name="statut")),
                ("provider_message_id", models.CharField(blank=True, max_length=200, verbose_name="ID provider")),
                ("error_message", models.TextField(blank=True, verbose_name="erreur")),
                ("retry_count", models.PositiveSmallIntegerField(default=0, verbose_name="retries")),
                ("max_retries", models.PositiveSmallIntegerField(default=3)),
                ("context", models.JSONField(blank=True, default=dict, verbose_name="variables contexte")),
                ("sent_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("template", models.ForeignKey(
                    blank=True, null=True, on_delete=models.deletion.SET_NULL,
                    related_name="email_logs", to="notifications.emailtemplate")),
                ("related_traveler", models.ForeignKey(
                    blank=True, null=True, on_delete=models.deletion.SET_NULL,
                    related_name="emails_received_logs", to="travelers.traveler")),
                ("related_user", models.ForeignKey(
                    blank=True, null=True, on_delete=models.deletion.SET_NULL,
                    related_name="emails_received_logs", to=settings.AUTH_USER_MODEL)),
                ("sent_by", models.ForeignKey(
                    blank=True, null=True, on_delete=models.deletion.SET_NULL,
                    related_name="emails_sent_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Journal email",
                "verbose_name_plural": "Journal des emails",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "-created_at"], name="notif_emaillog_status_created"),
                    models.Index(fields=["email_type", "-created_at"], name="notif_emaillog_type_created"),
                    models.Index(fields=["recipient"], name="notif_emaillog_recipient_idx"),
                ],
            },
        ),

        # ── PasswordResetToken ───────────────────────────────────────────
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token_hash", models.CharField(db_index=True, max_length=128, unique=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="password_reset_tokens",
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Token reset password",
                "verbose_name_plural": "Tokens reset password",
                "ordering": ["-created_at"],
            },
        ),

        # ── Seed initial ─────────────────────────────────────────────────
        migrations.RunPython(seed_sender_profiles, reverse_code=reverse_seed),
    ]
