import os

from .base import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Debug Toolbar — local only, and NOT during E2E: its fixed overlay intercepts
# pointer events over the cookie banner and other fixed UI, breaking Playwright.
if os.environ.get("E2E_TESTS") != "1":
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

# Celery: run tasks inline during dev / tests — no worker needed.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
