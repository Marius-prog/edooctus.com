from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import path, include
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import ConsentRecord, DataExportRequest, DataDeletionRequest, record_consent

app_name = "privacy"


class ConsentSer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ["id", "kind", "version", "granted", "granted_at", "revoked_at"]


class ExportSer(serializers.ModelSerializer):
    class Meta:
        model = DataExportRequest
        fields = ["id", "status", "requested_at", "ready_at",
                  "expires_at", "download_token"]
        read_only_fields = fields


class DeletionSer(serializers.ModelSerializer):
    class Meta:
        model = DataDeletionRequest
        fields = ["id", "reason", "status", "requested_at", "scheduled_for", "completed_at"]
        read_only_fields = ["status", "requested_at", "scheduled_for", "completed_at"]


class ConsentVS(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsentSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return ConsentRecord.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def grant_consent(request):
    """POST { kind, version, granted } -> create ConsentRecord."""
    kind = request.data.get("kind")
    version = request.data.get("version", "1")
    granted = bool(request.data.get("granted", True))
    if kind not in dict(ConsentRecord.KIND_CHOICES):
        return Response({"detail": "Unknown kind."}, status=400)
    rec = record_consent(
        request.user, kind, version, granted,
        ip_address=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )
    return Response(ConsentSer(rec).data, status=201)


class ExportVS(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExportSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return DataExportRequest.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def request_export(request):
    from .tasks import generate_export
    req = DataExportRequest.objects.create(user=request.user)
    generate_export.delay(req.id)  # eager in dev/tests
    req.refresh_from_db()
    return Response(ExportSer(req).data, status=202)


@api_view(["GET"])
def download_export(request, token):
    req = get_object_or_404(DataExportRequest, download_token=token,
                            status=DataExportRequest.STATUS_READY)
    if req.expires_at and req.expires_at < timezone.now():
        raise Http404("Expired.")
    if not req.file:
        raise Http404("No file.")
    req.status = DataExportRequest.STATUS_DOWNLOADED
    req.downloaded_at = timezone.now()
    req.save(update_fields=["status", "downloaded_at"])
    return FileResponse(req.file.open("rb"), as_attachment=True,
                        filename=f"my-data-{req.user_id}.json")


class DeletionVS(viewsets.ModelViewSet):
    serializer_class = DeletionSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return DataDeletionRequest.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@login_required
def settings_page(request):
    return render(request, "privacy/settings.html", {
        "consents": ConsentRecord.objects.filter(user=request.user),
        "exports": DataExportRequest.objects.filter(user=request.user)[:10],
        "deletions": DataDeletionRequest.objects.filter(user=request.user),
    })


router = DefaultRouter()
router.register(r"consents", ConsentVS, basename="consent")
router.register(r"exports", ExportVS, basename="export")
router.register(r"deletions", DeletionVS, basename="deletion")

urlpatterns = [
    path("", settings_page, name="settings"),
    path("policy/", lambda r: render(r, "privacy/policy.html"), name="policy"),
    path("api/", include(router.urls)),
    path("api/consent/", grant_consent, name="grant_consent"),
    path("api/export/request/", request_export, name="request_export"),
    path("download/<str:token>/", download_export, name="download_export"),
]
