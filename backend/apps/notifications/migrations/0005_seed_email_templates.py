"""Seed des EmailTemplate brandés (PUBLIC + INTERNAL).

Idempotent : utilise update_or_create par `code`.
"""
from django.db import migrations


def seed_templates(apps, schema_editor):
    from apps.notifications.email_html_layouts import DEFAULT_TEMPLATES

    EmailTemplate = apps.get_model("notifications", "EmailTemplate")
    SenderProfile = apps.get_model("notifications", "SenderProfile")

    for code, tpl in DEFAULT_TEMPLATES.items():
        sender = SenderProfile.objects.filter(code=tpl["sender_profile_code"]).first()
        EmailTemplate.objects.update_or_create(
            code=code,
            defaults={
                "name": tpl["name"],
                "email_type": tpl["email_type"],
                "subject": tpl["subject"],
                "body_html": tpl["body_html"],
                "body_text": tpl["body_text"],
                "sender_profile": sender,
                "variables_schema": tpl.get("variables_schema", {}),
                "is_active": True,
            },
        )


def remove_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("notifications", "EmailTemplate")
    EmailTemplate.objects.filter(code__in=[
        "admin_account_created",
        "admin_password_reset",
        "pass_confirmation",
        "followup_reminder",
        "followup_completed",
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_email_multi_sender"),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_code=remove_templates),
    ]
