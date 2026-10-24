"""Filtres de l'historique des notifications (/api/v1/notifications/)."""
from __future__ import annotations

import django_filters
from django.db.models import Q

from .models import Notification, NotificationStatus

# Regroupements utilisés par les indicateurs et les filtres rapides.
SENT_STATUSES = [NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ]
WAITING_STATUSES = [
    NotificationStatus.DRAFT, NotificationStatus.PENDING,
    NotificationStatus.QUEUED, NotificationStatus.ON_HOLD,
]
STATUS_GROUPS: dict[str, list[str]] = {
    "sent_all": SENT_STATUSES,
    "waiting": WAITING_STATUSES,
}


class NotificationFilter(django_filters.FilterSet):
    """Filtres combinables : période, statut(s), canal, fournisseur, maladie.

    - `status` accepte une valeur, une liste séparée par des virgules, ou un
      groupe (`sent_all` = envoyées + délivrées + lues, `waiting` = brouillon,
      en attente, en file ou en attente fournisseur).
    - `disease` : code maladie d'un suivi du voyageur destinataire.
    """

    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    status = django_filters.CharFilter(method="filter_status")
    disease = django_filters.CharFilter(method="filter_disease")

    class Meta:
        model = Notification
        fields = [
            "channel", "provider", "message_type", "direction",
            "traveler", "template", "error_code",
        ]

    def filter_status(self, queryset, name, value):
        values: list[str] = []
        for part in (value or "").split(","):
            part = part.strip()
            if not part:
                continue
            values.extend(STATUS_GROUPS.get(part, [part]))
        return queryset.filter(status__in=values) if values else queryset

    def filter_disease(self, queryset, name, value):
        code = (value or "").strip()
        if not code:
            return queryset
        return queryset.filter(
            Q(traveler__quarantines__disease__code__iexact=code)
            | Q(metadata__disease_code__iexact=code)
        ).distinct()
