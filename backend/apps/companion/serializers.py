"""
Serializers DRF du module Companion.

Tous les serializers acceptent un `public_id` voyageur en lookup (pas de
JWT côté PWA — le `public_id` joue le rôle de token suffisamment opaque
puisqu'il est généré aléatoirement et n'est connu que du voyageur).

Les rate-limits par scope sont configurés dans `urls.py` via
`ScopedRateThrottle`.
"""
from rest_framework import serializers

from .models import ConsentScope, LocationEventType


class ConsentRecordSerializer(serializers.Serializer):
    """Reçu lorsque le voyageur (dé)coche un scope dans la PWA."""

    public_id = serializers.CharField(max_length=24)
    scope = serializers.ChoiceField(choices=ConsentScope.choices)
    granted = serializers.BooleanField()
    consent_version = serializers.CharField(max_length=20, required=False, default="v1")
    text_excerpt = serializers.CharField(required=False, allow_blank=True, default="")
    revocation_reason = serializers.CharField(required=False, allow_blank=True, default="")


class CheckinSerializer(serializers.Serializer):
    """Check-in quotidien — version simplifiée et rassurante.

    Champs principaux :
    - `feeling` : auto-évaluation libre ("ok" / "symptom" / "assistance")
    - `symptoms` : dict booléen aligné sur SectionSymptoms du formulaire INHP
    - `temperature_celsius` : optionnel
    - `notes` : champ libre court
    - `location` : optionnel, ne sera enregistré que si consentement actif

    NB : le check-in crée un `quarantine.DailyCheck` côté DB ; la table
    `companion` ne stocke pas les check-ins (elle ne fait que le routage et
    les pings de localisation associés).
    """

    public_id = serializers.CharField(max_length=24)
    feeling = serializers.ChoiceField(
        choices=[("ok", "ok"), ("symptom", "symptom"), ("assistance", "assistance")],
        default="ok",
    )
    symptoms = serializers.DictField(child=serializers.BooleanField(), required=False, default=dict)
    temperature_celsius = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=30, max_value=45,
        required=False, allow_null=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    needs_contact = serializers.BooleanField(required=False, default=False)

    # Position optionnelle (jointe au check-in si consentement géoloc OK)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)


class LocationPingSerializer(serializers.Serializer):
    """Ping de position envoyé indépendamment d'un check-in.

    Réservé aux actions volontaires : bouton "Partager ma position" /
    "J'ai besoin d'aide" / clic sur une notification d'assistance.
    """

    public_id = serializers.CharField(max_length=24)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    accuracy_m = serializers.FloatField(required=False, allow_null=True)
    altitude_m = serializers.FloatField(required=False, allow_null=True)
    speed_mps = serializers.FloatField(required=False, allow_null=True)
    heading_deg = serializers.FloatField(required=False, allow_null=True)
    event_type = serializers.ChoiceField(
        choices=LocationEventType.choices, required=False,
        default=LocationEventType.MANUAL_SHARE,
    )
    device_info = serializers.CharField(required=False, allow_blank=True, max_length=200)


class PushSubscribeSerializer(serializers.Serializer):
    """Payload retourné par `pushManager.subscribe()` côté navigateur,
    forwardé tel quel par le client à notre endpoint d'enregistrement.

    Format attendu (W3C PushSubscription) :
    {
      "public_id": "TRV-XXX",
      "subscription": {
        "endpoint": "https://fcm.googleapis.com/...",
        "keys": {"p256dh": "...", "auth": "..."}
      },
      "user_agent": "Mozilla/5.0 ...",
      "device_type": "mobile",
      "locale": "fr-FR"
    }
    """

    public_id = serializers.CharField(max_length=24)
    subscription = serializers.DictField()
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=300)
    device_type = serializers.CharField(required=False, allow_blank=True, max_length=10)
    locale = serializers.CharField(required=False, allow_blank=True, max_length=10)

    def validate_subscription(self, value):
        endpoint = value.get("endpoint")
        keys = value.get("keys") or {}
        if not endpoint:
            raise serializers.ValidationError("`endpoint` manquant.")
        if not keys.get("p256dh") or not keys.get("auth"):
            raise serializers.ValidationError("`keys.p256dh` et `keys.auth` requis.")
        return value


class PushUnsubscribeSerializer(serializers.Serializer):
    public_id = serializers.CharField(max_length=24)
    endpoint = serializers.URLField(max_length=500)
