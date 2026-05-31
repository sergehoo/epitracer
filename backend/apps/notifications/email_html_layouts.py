"""Layouts HTML brandés pour les emails EpiTrace.

Deux profils visuels :
  - PUBLIC   : aux couleurs Destination CI / République de Côte d'Ivoire
               (orange #F77F00 + vert #009B5A), pour les voyageurs.
  - INTERNAL : style INHP / institutionnel sobre, pour l'administration.

Les templates sont écrits en HTML inline (CSS dans `style=`) parce que les
clients email (Outlook, Gmail mobile, Apple Mail) ignorent les feuilles CSS
externes ou <style> dans <head>. Tableau-based layout pour compat Outlook.
"""
from __future__ import annotations

# ----------------------------------------------------------------------------
# COULEURS DE MARQUE
# ----------------------------------------------------------------------------
CI_ORANGE = "#F77F00"
CI_GREEN = "#009B5A"
CI_DARK = "#064E3B"
INHP_BLUE = "#1E40AF"
SLATE_50 = "#F8FAFC"
SLATE_100 = "#F1F5F9"
SLATE_300 = "#CBD5E1"
SLATE_500 = "#64748B"
SLATE_700 = "#334155"
SLATE_900 = "#0F172A"


# ----------------------------------------------------------------------------
# LAYOUT PUBLIC — Destination CI (orange + vert + ton chaleureux)
# ----------------------------------------------------------------------------
def public_layout(
    *,
    title: str,
    intro: str = "",
    body_blocks: str = "",
    cta_label: str | None = None,
    cta_url: str | None = None,
    footer_extra: str = "",
) -> str:
    """Wraps un contenu dans le layout public Destination CI."""
    cta_html = ""
    if cta_label and cta_url:
        cta_html = f"""
<tr><td align="center" style="padding:24px 0 8px 0">
  <a href="{cta_url}" style="display:inline-block;background:{CI_ORANGE};
     color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;
     font-weight:700;font-size:15px;font-family:Arial,sans-serif">
    {cta_label}
  </a>
</td></tr>"""

    intro_html = (
        f"""<tr><td style="padding:0 32px 16px 32px;color:{SLATE_700};
        font-family:Arial,sans-serif;font-size:15px;line-height:1.6">{intro}</td></tr>"""
        if intro else ""
    )

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title></head>
<body style="margin:0;padding:0;background:{SLATE_100};
  font-family:Arial,Helvetica,sans-serif;color:{SLATE_900}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{SLATE_100};padding:24px 0">
 <tr><td align="center">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0"
         style="max-width:600px;background:#ffffff;border-radius:16px;
                overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06)">

    <!-- Bandeau institutionnel -->
    <tr><td style="background:linear-gradient(135deg,{CI_ORANGE} 0%,{CI_GREEN} 100%);
       padding:20px 32px;color:#ffffff">
      <table width="100%"><tr>
        <td style="font-family:Arial,sans-serif;font-weight:700;font-size:18px;
                   letter-spacing:0.5px">
          Destination Côte d'Ivoire
        </td>
        <td align="right" style="font-family:Arial,sans-serif;font-size:11px;
                                 text-transform:uppercase;letter-spacing:1.5px;
                                 opacity:0.9">
          Accompagnement voyageur
        </td>
      </tr></table>
    </td></tr>

    <!-- Titre -->
    <tr><td style="padding:32px 32px 12px 32px">
      <h1 style="margin:0;color:{CI_DARK};font-family:Arial,sans-serif;
                 font-size:24px;font-weight:800;line-height:1.3">{title}</h1>
    </td></tr>

    {intro_html}

    <!-- Body blocks -->
    <tr><td style="padding:0 32px 8px 32px;color:{SLATE_700};
       font-family:Arial,sans-serif;font-size:15px;line-height:1.7">
       {body_blocks}
    </td></tr>

    {cta_html}

    <!-- Encart aide -->
    <tr><td style="padding:24px 32px">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:{SLATE_50};border-left:4px solid {CI_GREEN};
                    border-radius:8px;padding:14px 16px">
        <tr><td style="font-family:Arial,sans-serif;font-size:13px;
                       color:{SLATE_700};line-height:1.6">
          Besoin d'assistance ? Appelez le <strong>143</strong>
          (gratuit, 24h/24) ou écrivez à
          <a href="mailto:infos@destinationci.com"
             style="color:{CI_ORANGE};text-decoration:none">infos@destinationci.com</a>.
        </td></tr>
      </table>
    </td></tr>

    {footer_extra}

    <!-- Footer légal -->
    <tr><td style="background:{CI_DARK};color:#cbd5e1;padding:20px 32px;
       font-family:Arial,sans-serif;font-size:12px;line-height:1.6">
      <strong style="color:#ffffff">Ministère de la Santé, de l'Hygiène Publique
      et de la Couverture Maladie Universelle</strong><br/>
      Institut National d'Hygiène Publique &middot; République de Côte d'Ivoire<br/>
      <span style="font-style:italic;opacity:0.7">Union &middot; Discipline &middot; Travail</span>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:12px 0"/>
      <span style="font-size:11px;opacity:0.8">
        Cet email vous est envoyé dans le cadre du dispositif national de
        veille sanitaire. Vos données sont traitées conformément au
        Règlement Général sur la Protection des Données (RGPD) et à la
        loi ivoirienne 2013-450 sur la protection des données personnelles.
        Pour exercer vos droits, écrivez à
        <a href="mailto:dpo@destinationci.com" style="color:#ffd591">dpo@destinationci.com</a>.
      </span>
    </td></tr>

  </table>
 </td></tr>
</table>
</body></html>"""


# ----------------------------------------------------------------------------
# LAYOUT INTERNAL — INHP institutionnel (sobre, professionnel)
# ----------------------------------------------------------------------------
def internal_layout(
    *,
    title: str,
    intro: str = "",
    body_blocks: str = "",
    cta_label: str | None = None,
    cta_url: str | None = None,
    security_notice: str = "",
) -> str:
    """Wraps un contenu dans le layout interne INHP."""
    cta_html = ""
    if cta_label and cta_url:
        cta_html = f"""
<tr><td align="center" style="padding:24px 0 8px 0">
  <a href="{cta_url}" style="display:inline-block;background:{INHP_BLUE};
     color:#ffffff;text-decoration:none;padding:13px 30px;border-radius:6px;
     font-weight:700;font-size:14px;font-family:Arial,sans-serif">
    {cta_label}
  </a>
</td></tr>"""

    intro_html = (
        f"""<tr><td style="padding:0 32px 16px 32px;color:{SLATE_700};
        font-family:Arial,sans-serif;font-size:14px;line-height:1.6">{intro}</td></tr>"""
        if intro else ""
    )

    security_html = ""
    if security_notice:
        security_html = f"""
<tr><td style="padding:8px 32px 24px 32px">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#FEF3C7;border-left:4px solid #D97706;
                border-radius:6px;padding:12px 14px">
    <tr><td style="font-family:Arial,sans-serif;font-size:12px;
                   color:#92400E;line-height:1.5">
      <strong>Sécurité :</strong> {security_notice}
    </td></tr>
  </table>
</td></tr>"""

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title></head>
<body style="margin:0;padding:0;background:{SLATE_100};
  font-family:Arial,Helvetica,sans-serif;color:{SLATE_900}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{SLATE_100};padding:24px 0">
 <tr><td align="center">
  <table role="presentation" width="580" cellpadding="0" cellspacing="0"
         style="max-width:580px;background:#ffffff;border-radius:8px;
                overflow:hidden;border:1px solid {SLATE_300}">

    <!-- En-tête INHP -->
    <tr><td style="background:{INHP_BLUE};padding:18px 28px;color:#ffffff">
      <table width="100%"><tr>
        <td style="font-family:Arial,sans-serif;font-weight:700;font-size:16px">
          INHP &middot; Veille Sanitaire
        </td>
        <td align="right" style="font-family:Arial,sans-serif;font-size:11px;
                                 opacity:0.85;text-transform:uppercase;
                                 letter-spacing:1px">
          Console administration
        </td>
      </tr></table>
    </td></tr>

    <!-- Titre -->
    <tr><td style="padding:28px 32px 8px 32px">
      <h1 style="margin:0;color:{SLATE_900};font-family:Arial,sans-serif;
                 font-size:20px;font-weight:700;line-height:1.3">{title}</h1>
    </td></tr>

    {intro_html}

    <!-- Body blocks -->
    <tr><td style="padding:0 32px 8px 32px;color:{SLATE_700};
       font-family:Arial,sans-serif;font-size:14px;line-height:1.7">
       {body_blocks}
    </td></tr>

    {cta_html}

    {security_html}

    <!-- Footer institutionnel -->
    <tr><td style="background:{SLATE_50};border-top:1px solid {SLATE_300};
       padding:18px 32px;font-family:Arial,sans-serif;font-size:11px;
       color:{SLATE_500};line-height:1.6">
      <strong style="color:{SLATE_700}">Institut National d'Hygiène Publique</strong>
      &middot; Veille Sanitaire EpiTrace<br/>
      Ministère de la Santé, de l'Hygiène Publique et de la Couverture Maladie Universelle<br/>
      <hr style="border:none;border-top:1px solid {SLATE_300};margin:10px 0"/>
      Email automatique destiné aux agents et administrateurs habilités.
      Ne pas transférer à l'extérieur. Pour toute question, contactez
      <a href="mailto:inhp@veillesanitaire.com" style="color:{INHP_BLUE}">inhp@veillesanitaire.com</a>.
    </td></tr>

  </table>
 </td></tr>
</table>
</body></html>"""


# ----------------------------------------------------------------------------
# TEMPLATES DE BODY (variables {var} substituées par EmailRouter._render)
# ----------------------------------------------------------------------------

# ── INTERNAL — Création compte admin ────────────────────────────────────────
ADMIN_ACCOUNT_CREATED_HTML = internal_layout(
    title="Création de votre compte",
    intro="Bonjour <strong>{full_name}</strong>, votre compte vient d'être "
          "créé sur la console INHP Veille Sanitaire (plateforme EpiTrace).",
    body_blocks=f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;margin:8px 0 0 0">
  <tr><td style="padding:8px 14px;background:{SLATE_50};
                 border:1px solid {SLATE_300};border-radius:4px 0 0 0;
                 font-weight:600;color:{SLATE_700};width:160px">Identifiant</td>
      <td style="padding:8px 14px;border:1px solid {SLATE_300};border-left:none;
                 border-radius:0 4px 0 0">
        <code style="font-family:Consolas,monospace;font-size:13px;color:{SLATE_900}">{{username}}</code>
      </td></tr>
  <tr><td style="padding:8px 14px;background:{SLATE_50};
                 border:1px solid {SLATE_300};border-top:none;
                 font-weight:600;color:{SLATE_700}">Rôle(s) attribué(s)</td>
      <td style="padding:8px 14px;border:1px solid {SLATE_300};
                 border-top:none;border-left:none">{{roles}}</td></tr>
  <tr><td style="padding:8px 14px;background:{SLATE_50};
                 border:1px solid {SLATE_300};border-top:none;
                 font-weight:600;color:{SLATE_700}">Mot de passe temporaire</td>
      <td style="padding:8px 14px;border:1px solid {SLATE_300};
                 border-top:none;border-left:none">
        <code style="font-family:Consolas,monospace;font-size:14px;font-weight:700;
                     color:{INHP_BLUE};background:#EFF6FF;padding:3px 8px;
                     border-radius:4px">{{temporary_password}}</code>
      </td></tr>
</table>
<p style="margin:16px 0 0 0">Connectez-vous à l'adresse suivante pour activer votre compte :</p>
""",
    cta_label="Accéder à la console",
    cta_url="{admin_login_url}",
    security_notice=(
        "À votre première connexion, vous serez invité à modifier le mot de passe "
        "temporaire. Celui-ci expire dans <strong>24 heures</strong>. "
        "Si vous n'êtes pas à l'origine de cette demande, contactez immédiatement "
        "l'administrateur national."
    ),
)

ADMIN_ACCOUNT_CREATED_TEXT = """
Bonjour {full_name},

Votre compte a été créé sur la console INHP Veille Sanitaire.

  Identifiant         : {username}
  Rôle(s)             : {roles}
  Mot de passe temp.  : {temporary_password}

Connexion : {admin_login_url}

SÉCURITÉ : modification du mot de passe obligatoire à la première
connexion. Le mot de passe temporaire expire dans 24 heures.

— INHP Veille Sanitaire
""".strip()


# ── INTERNAL — Reset password ────────────────────────────────────────────────
ADMIN_PASSWORD_RESET_HTML = internal_layout(
    title="Réinitialisation de votre mot de passe",
    intro="Bonjour <strong>{full_name}</strong>, une demande de réinitialisation "
          "de votre mot de passe a été enregistrée sur la console INHP.",
    body_blocks="""
<p>Pour définir un nouveau mot de passe, cliquez sur le bouton ci-dessous.</p>
<p style="font-size:12px;color:#64748B">
  Si vous n'arrivez pas à cliquer, copiez ce lien :<br/>
  <code style="word-break:break-all;font-size:11px">{reset_url}</code>
</p>
""",
    cta_label="Réinitialiser mon mot de passe",
    cta_url="{reset_url}",
    security_notice=(
        "Ce lien est valable <strong>{ttl_hours} heures</strong> et ne peut "
        "être utilisé qu'<strong>une seule fois</strong>. Si vous n'êtes pas "
        "à l'origine de cette demande, ignorez ce message et changez "
        "immédiatement votre mot de passe via la console."
    ),
)

ADMIN_PASSWORD_RESET_TEXT = """
Bonjour {full_name},

Une demande de réinitialisation de votre mot de passe a été enregistrée
sur la console INHP Veille Sanitaire.

Pour définir un nouveau mot de passe, ouvrez ce lien :
{reset_url}

Ce lien expire dans {ttl_hours} heures et ne peut être utilisé qu'une fois.

Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.

— INHP Veille Sanitaire
""".strip()


# ── PUBLIC — Confirmation pass ───────────────────────────────────────────────
PASS_CONFIRMATION_HTML = public_layout(
    title="Votre pass sanitaire est prêt",
    intro="Bonjour <strong>{full_name}</strong>, votre fiche d'accompagnement "
          "sanitaire vient d'être enregistrée. Voici les informations utiles "
          "pour votre arrivée en Côte d'Ivoire.",
    body_blocks=f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px">
  <tr><td style="padding:10px 14px;background:{SLATE_50};
                 border:1px solid {SLATE_300};font-weight:600;
                 color:{SLATE_700};width:170px">N° de pass</td>
      <td style="padding:10px 14px;border:1px solid {SLATE_300};border-left:none">
        <code style="font-family:Consolas,monospace;font-size:13px;
                     color:{CI_DARK};font-weight:700">{{pass_number}}</code>
      </td></tr>
  <tr><td style="padding:10px 14px;background:{SLATE_50};
                 border:1px solid {SLATE_300};border-top:none;
                 font-weight:600;color:{SLATE_700}">Valable jusqu'au</td>
      <td style="padding:10px 14px;border:1px solid {SLATE_300};
                 border-top:none;border-left:none">{{expires_at}}</td></tr>
</table>
<p style="margin:18px 0 0 0">
  <strong>À l'arrivée :</strong> présentez votre QR code à un agent INHP au point
  d'entrée (aéroport, port ou frontière terrestre). Le contrôle dure moins de
  30 secondes.
</p>
<p>
  <strong>Pendant 21 jours :</strong> vous recevrez chaque jour un message
  de suivi sanitaire. Répondez-y rapidement pour faciliter votre accompagnement.
</p>
""",
    cta_label="Consulter mon pass en ligne",
    cta_url="{pass_url}",
)

PASS_CONFIRMATION_TEXT = """
Bonjour {full_name},

Votre pass sanitaire est prêt :

  N° de pass     : {pass_number}
  Valable jusqu'au : {expires_at}

À l'arrivée, présentez votre QR code à un agent INHP au point d'entrée.

Pendant 21 jours, vous recevrez un message quotidien de suivi sanitaire.
Besoin d'assistance : appelez le 143 (gratuit).

— Destination Côte d'Ivoire / INHP
""".strip()


# ── PUBLIC — Rappel suivi 21 jours ───────────────────────────────────────────
FOLLOWUP_REMINDER_HTML = public_layout(
    title="Votre suivi sanitaire du jour",
    intro="Bonjour <strong>{full_name}</strong>, c'est l'heure de votre "
          "check-in sanitaire quotidien (jour <strong>{day}</strong>/21).",
    body_blocks="""
<p>Quelques secondes suffisent pour confirmer votre état de santé et
faciliter votre accompagnement par les équipes INHP.</p>
<p>Si vous présentez des symptômes (fièvre, fatigue intense, maux de tête,
saignements inhabituels), appelez le <strong>143</strong> immédiatement.</p>
""",
    cta_label="Faire mon check-in",
    cta_url="{checkin_url}",
)

FOLLOWUP_REMINDER_TEXT = """
Bonjour {full_name},

C'est l'heure de votre check-in sanitaire (jour {day}/21).

→ {checkin_url}

Si vous présentez des symptômes (fièvre, fatigue, maux de tête, saignements
inhabituels), appelez le 143 immédiatement.

— Destination Côte d'Ivoire / INHP
""".strip()


# ── PUBLIC — Fin de suivi ────────────────────────────────────────────────────
FOLLOWUP_COMPLETED_HTML = public_layout(
    title="Votre suivi est terminé — Merci !",
    intro="Bonjour <strong>{full_name}</strong>, vous arrivez au terme de "
          "vos 21 jours de suivi sanitaire en Côte d'Ivoire.",
    body_blocks="""
<p>Au nom du Ministère de la Santé et de l'INHP, nous vous remercions
sincèrement pour votre coopération tout au long de cet accompagnement.</p>
<p>Votre contribution active à la veille sanitaire nationale renforce
la protection collective de tous les voyageurs et de la population
ivoirienne.</p>
<p style="background:#FEF3C7;border-left:4px solid #D97706;padding:10px 14px;
border-radius:6px;color:#92400E">
  <strong>Recommandation :</strong> en cas d'apparition de symptômes
  inhabituels dans les jours qui suivent, n'hésitez pas à consulter
  un médecin et à mentionner votre séjour récent.
</p>
""",
)


# ----------------------------------------------------------------------------
# REGISTRE — utilisé par les Celery tasks et la migration de seed
# ----------------------------------------------------------------------------
DEFAULT_TEMPLATES = {
    "admin_account_created": {
        "name": "Création de compte administrateur",
        "email_type": "admin_account_created",
        "sender_profile_code": "internal",
        "subject": "Création de votre compte — Console INHP Veille Sanitaire",
        "body_html": ADMIN_ACCOUNT_CREATED_HTML,
        "body_text": ADMIN_ACCOUNT_CREATED_TEXT,
        "variables_schema": {
            "full_name": "string",
            "username": "string",
            "roles": "string",
            "temporary_password": "string",
            "admin_login_url": "string",
        },
    },
    "admin_password_reset": {
        "name": "Réinitialisation mot de passe administrateur",
        "email_type": "admin_password_reset",
        "sender_profile_code": "internal",
        "subject": "Réinitialisation de votre mot de passe — INHP Veille Sanitaire",
        "body_html": ADMIN_PASSWORD_RESET_HTML,
        "body_text": ADMIN_PASSWORD_RESET_TEXT,
        "variables_schema": {
            "full_name": "string",
            "reset_url": "string",
            "ttl_hours": "number",
        },
    },
    "pass_confirmation": {
        "name": "Confirmation pass sanitaire voyageur",
        "email_type": "pass_confirmation",
        "sender_profile_code": "public",
        "subject": "Votre fiche d'accompagnement sanitaire est disponible",
        "body_html": PASS_CONFIRMATION_HTML,
        "body_text": PASS_CONFIRMATION_TEXT,
        "variables_schema": {
            "full_name": "string",
            "pass_number": "string",
            "expires_at": "string",
            "pass_url": "string",
        },
    },
    "followup_reminder": {
        "name": "Rappel quotidien de suivi 21 jours",
        "email_type": "followup_reminder",
        "sender_profile_code": "public",
        "subject": "Suivi sanitaire — Jour {day}",
        "body_html": FOLLOWUP_REMINDER_HTML,
        "body_text": FOLLOWUP_REMINDER_TEXT,
        "variables_schema": {
            "full_name": "string",
            "day": "number",
            "checkin_url": "string",
        },
    },
    "followup_completed": {
        "name": "Fin de suivi sanitaire",
        "email_type": "followup_completed",
        "sender_profile_code": "public",
        "subject": "Merci pour votre coopération — Fin de suivi sanitaire",
        "body_html": FOLLOWUP_COMPLETED_HTML,
        "body_text": "Bonjour {full_name},\n\nVotre suivi de 21 jours est terminé. Merci pour votre coopération.\n\n— Destination Côte d'Ivoire / INHP",
        "variables_schema": {"full_name": "string"},
    },
}
