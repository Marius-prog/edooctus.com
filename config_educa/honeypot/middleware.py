"""Scanner-probe tripwire middleware.

FAIL-OPEN by design: it only ever *adds* a log+alert for requests whose path
matches a known attacker-probe pattern, then returns a believable 404. For every
other request it is a single regex check and a pass-through — it can never alter,
block, or slow a legitimate response (the whole body is guarded by try/except).

Explicitly-routed lures (/admin/, /.env, /api/v1/users, …) are handled by views,
NOT here, so there is no double-logging.
"""
import re

from django.http import HttpResponseNotFound

# Common automated-scanner probes that are NOT real routes and NOT explicit lures.
_PROBE_PATTERNS = [
    re.compile(p) for p in (
        r"^/\.git(/|$)",
        r"^/\.aws(/|$)",
        r"^/\.ssh(/|$)",
        r"^/phpmyadmin",
        r"^/pma(/|$)",
        r"^/xmlrpc\.php$",
        r"^/wp-content(/|$)",
        r"^/vendor/",
        r"^/\.svn(/|$)",
        r"^/config\.(php|json|yml|yaml)$",
        r"^/server-status$",
        r"^/actuator(/|$)",
    )
]


def _is_probe(path: str) -> bool:
    return any(p.match(path) for p in _PROBE_PATTERNS)


class HoneypotProbeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if _is_probe(request.path):
                from .alerts import record_and_alert
                from .models import HoneypotEvent
                record_and_alert(request, HoneypotEvent.EXPOSED_FILE,
                                 metadata={"probe": True})
                return HttpResponseNotFound("Not Found")
        except Exception:  # pragma: no cover — never break a real request
            pass
        return self.get_response(request)
