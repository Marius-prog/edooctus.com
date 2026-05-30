"""Honeypot lure views + staff dashboard.

None of the lures ever authenticate a user or expose real data. The fake admin
login always "fails"; decoy endpoints return fabricated bait built from
DecoyAccount rows only.
"""
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .alerts import record_and_alert
from .models import DecoyAccount, HoneypotEvent

_FAILED_LOGIN_MSG = (
    "Please enter the correct username and password for a staff account. "
    "Note that both fields may be case-sensitive."
)


@csrf_exempt
def fake_admin_login(request):
    """Django-admin lookalike. Logs every POST; never authenticates anyone."""
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        event_type = (
            HoneypotEvent.DECOY_ACCOUNT_LOGIN
            if username and DecoyAccount.objects.filter(username=username).exists()
            else HoneypotEvent.FAKE_ADMIN_LOGIN
        )
        record_and_alert(request, event_type,
                         attempted_username=username, attempted_password=password)
        return render(request, "honeypot/fake_admin_login.html",
                      {"error": _FAILED_LOGIN_MSG}, status=200)
    return render(request, "honeypot/fake_admin_login.html", {})


@csrf_exempt
def exposed_file(request):
    """Bait for exposed-secret scanners (/.env, /backup.sql)."""
    record_and_alert(request, HoneypotEvent.EXPOSED_FILE)
    return HttpResponse(
        "# environment\nAPP_ENV=production\nDB_HOST=10.0.0.5\n"
        "SECRET_KEY=PLACEHOLDER-NOT-A-REAL-KEY\n",
        content_type="text/plain",
    )


def decoy_api_users(request):
    """Fake 'user dump' endpoint — returns DecoyAccount bait only."""
    record_and_alert(request, HoneypotEvent.DECOY_ENDPOINT)
    results = [
        {"id": d.id, "username": d.username, "role": d.display_role, "email": d.email}
        for d in DecoyAccount.objects.all()[:25]
    ]
    return JsonResponse({"count": len(results), "results": results})


@csrf_exempt
def tripwire(request, token):
    """Hit only by something that followed the hidden nofollow tripwire link."""
    record_and_alert(request, HoneypotEvent.TRIPWIRE, metadata={"token": token})
    return HttpResponseNotFound("Not Found")


@staff_member_required
def dashboard(request):
    """Staff-only threat-intel dashboard."""
    now = timezone.now()
    last24 = now - timedelta(hours=24)
    last7 = now - timedelta(days=7)
    qs = HoneypotEvent.objects.all()

    ctx = {
        "total_events": qs.count(),
        "events_24h": qs.filter(created__gte=last24).count(),
        "events_7d": qs.filter(created__gte=last7).count(),
        "unique_ips": qs.exclude(ip_address__isnull=True)
                        .values("ip_address").distinct().count(),
        "decoy_hits": qs.filter(event_type=HoneypotEvent.DECOY_ACCOUNT_LOGIN).count(),
        "by_type": list(qs.values("event_type").annotate(n=Count("id")).order_by("-n")),
        "top_paths": list(qs.values("path").annotate(n=Count("id")).order_by("-n")[:10]),
        "top_ips": list(qs.exclude(ip_address__isnull=True)
                          .values("ip_address").annotate(n=Count("id")).order_by("-n")[:10]),
        "recent": qs[:25],
        "activity_bars": _activity_bars(qs),
    }
    return render(request, "honeypot/dashboard.html", ctx)


def _activity_bars(qs, days=14, max_height=32):
    """Per-day event counts as bar heights (mirrors students dashboard sparkline)."""
    today = timezone.now().date()
    start = today - timedelta(days=days - 1)
    counts = {start + timedelta(days=i): 0 for i in range(days)}
    for ev in qs.filter(created__date__gte=start):
        d = ev.created.date()
        if d in counts:
            counts[d] += 1
    values = [counts[start + timedelta(days=i)] for i in range(days)]
    peak = max(values) or 1
    return [
        {"v": v, "h": round((v / peak) * max_height) if v else 1,
         "y": max_height - (round((v / peak) * max_height) if v else 1)}
        for v in values
    ]
