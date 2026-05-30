import os
from django.core.exceptions import ImproperlyConfigured
from .base import *

DEBUG = False

# Fail fast if critical secrets are missing in production.
_SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not _SECRET_KEY or _SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY environment variable must be set to a strong, '
        'unique value in production.'
    )
SECRET_KEY = _SECRET_KEY

for _required in ('POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'):
    if not os.environ.get(_required):
        raise ImproperlyConfigured(
            f'{_required} environment variable must be set in production.'
        )
ADMINS = [
    ('Marius S', 'msabaliauskas@gmail.com'),
]
ALLOWED_HOSTS = ['educto.io', 'www.educto.io', 'localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': 'db',
        'PORT': 5432,
    }
}
REDIS_URL = 'redis://cache:6379'
CACHES['default']['LOCATION'] = REDIS_URL
CHANNEL_LAYERS['default']['CONFIG']['hosts'] = [REDIS_URL]

# --- Email (SMTP) ---------------------------------------------------------
# Override base.py's console backend with real SMTP in production.
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_TIMEOUT = 30
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_FROM_EMAIL', 'noreply@educto.io')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Security
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
