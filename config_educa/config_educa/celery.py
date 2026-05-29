"""Celery application bootstrap.

Run a worker locally:
    celery -A config_educa worker -l info
Run beat (periodic tasks):
    celery -A config_educa beat -l info
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_educa.settings.local")

app = Celery("config_educa")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
