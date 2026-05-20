from django.urls import path

from .consumers import AlertConsumer, TravelerStreamConsumer

websocket_urlpatterns = [
    path("ws/alerts/", AlertConsumer.as_asgi()),
    path("ws/travelers/", TravelerStreamConsumer.as_asgi()),
]
