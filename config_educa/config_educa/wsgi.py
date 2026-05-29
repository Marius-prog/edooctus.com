"""
WSGI config for config_educa project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Production entrypoint: default to prod settings unless explicitly overridden
# (compose sets this anyway; the default keeps a stray server from booting in DEBUG).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_educa.settings.prod')

application = get_wsgi_application()
