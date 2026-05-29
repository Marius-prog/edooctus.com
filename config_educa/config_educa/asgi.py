import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
import chat.routing

# Production entrypoint: default to prod settings unless explicitly overridden
# (compose sets this anyway; the default keeps a stray server from booting in DEBUG).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_educa.settings.prod')
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(chat.routing.websocket_urlpatterns)
        )
    ),
})
