"""Services métier du module notifications.

Architecture :
    router.py            → décide quel provider utiliser selon le n°
    sms_orange_ci.py     → impl. envoi SMS Orange Côte d'Ivoire (OAuth)
    sms_twilio.py        → impl. envoi SMS Twilio (international)
    dispatcher.py        → orchestre : routage + envoi + persistance
    audit.py             → helper pour logger les actions en DB
"""
from .router import (
    NotificationProviderRouter,
    detect_provider,
    is_ivoirian_number,
    normalize_phone_number,
    validate_phone_number,
)
from .dispatcher import (
    SendResult,
    enqueue_notification,
    send_manual_message,
    send_template_message,
)

__all__ = [
    "NotificationProviderRouter",
    "detect_provider",
    "is_ivoirian_number",
    "normalize_phone_number",
    "validate_phone_number",
    "SendResult",
    "enqueue_notification",
    "send_manual_message",
    "send_template_message",
]
