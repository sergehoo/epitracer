"""Migration : MFA par email + champs sécurité auth.

- Ajoute User.locked_at, locked_until, failed_login_attempts, must_change_password
- Crée le modèle EmailOtpCode (codes OTP 6 chiffres hashés)
- Ajoute table historique HistoricalUser pour les nouveaux champs
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_role_label_mshpcmu"),
    ]

    operations = [
        # ── Nouveaux champs User ─────────────────────────────────────────
        migrations.AddField(
            model_name="user",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="locked_until",
            field=models.DateTimeField(
                blank=True, null=True,
                help_text="Verrouillage temporaire automatique.",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="failed_login_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                help_text="Force le changement de mot de passe à la prochaine connexion.",
            ),
        ),
        # ── Historicalrecords (simple_history) — mêmes champs sur la table d'historique
        migrations.AddField(
            model_name="historicaluser",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicaluser",
            name="locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicaluser",
            name="failed_login_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="historicaluser",
            name="must_change_password",
            field=models.BooleanField(default=False),
        ),

        # ── EmailOtpCode ────────────────────────────────────────────────
        migrations.CreateModel(
            name="EmailOtpCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(editable=False, null=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("code_hash", models.CharField(db_index=True, max_length=128, verbose_name="hash du code")),
                ("expires_at", models.DateTimeField(db_index=True, verbose_name="expire à")),
                ("attempts", models.PositiveSmallIntegerField(default=0, verbose_name="tentatives")),
                ("max_attempts", models.PositiveSmallIntegerField(default=5)),
                ("used_at", models.DateTimeField(blank=True, null=True, verbose_name="utilisé le")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="email_otp_codes",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Code OTP email",
                "verbose_name_plural": "Codes OTP email",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "-created_at"], name="acct_otp_user_created_idx"),
                    models.Index(fields=["expires_at"], name="acct_otp_expires_idx"),
                ],
            },
        ),
    ]
