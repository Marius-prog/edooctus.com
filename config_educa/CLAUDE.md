# CLAUDE.md (config_educa/)

Django project root — run all `manage.py` commands from here. See the repo-root
`CLAUDE.md` for full architecture, commands, settings, testing, and deployment.

## Module-specific notes

- **Settings**: `config_educa/settings/{base,local,prod}.py`. `base.py` defaults
  `DEBUG=False`; `local.py` opts into `DEBUG=True` + SQLite + eager Celery.
  `wsgi.py`/`asgi.py` default `DJANGO_SETTINGS_MODULE` to `...settings.prod`.
- **Tests**: Django test runner (not pytest), e.g.
  `DJANGO_SETTINGS_MODULE=config_educa.settings.local python manage.py test <app>`.
  Redis must be running for `students`/`chat` tests.
- **DRF authz**: object-level writes use `shared.permissions.IsOwnerOrReadOnly`
  (set `owner_field` on a viewset; defaults to `user`). Quiz attempts gate on
  enrollment via `quizzes.views.user_can_attempt`.
- **Async**: `config_educa/celery.py` defines the Celery app; `__init__.py`
  imports it, so `celery` must be installed even for local runs.
