"""Consumers WebSocket pour le dashboard temps réel."""
from __future__ import annotations

import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class AlertConsumer(AsyncJsonWebsocketConsumer):
    """Pousse les alertes sanitaires en temps réel aux tableaux de bord connectés."""

    GROUP = "alerts"

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(self.GROUP, self.channel_name)
        await self.accept()
        await self.send_json({"type": "ready", "data": {"channel": "alerts"}})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Le client peut envoyer un "ping" pour vérifier la connexion
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def alert_message(self, event):
        """Reçu via group_send (apps.surveillance.services.broadcast_alert)."""
        await self.send_json({"type": "alert", "data": event["data"]})


class TravelerStreamConsumer(AsyncJsonWebsocketConsumer):
    """Stream d'évènements voyageurs (création, MAJ statut)."""

    GROUP = "travelers"

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(self.GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

    async def traveler_event(self, event):
        await self.send_json({"type": "traveler", "data": event["data"]})
