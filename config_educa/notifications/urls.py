from django.urls import path, include
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import Notification, NotificationPreference, unread_count

app_name = "notifications"


class NotifSer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "channel",
                  "is_read", "read_at", "created", "metadata"]
        read_only_fields = fields


class PrefSer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        exclude = ["id", "user"]


class NotifVS(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotifSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        n = self.get_object()
        n.mark_read()
        return Response(NotifSer(n).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        from django.utils import timezone
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now(),
        )
        return Response({"unread": 0})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def unread(request):
    return Response({"unread": unread_count(request.user)})


@api_view(["GET", "PUT"])
@permission_classes([permissions.IsAuthenticated])
def prefs(request):
    p, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "PUT":
        ser = PrefSer(p, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
    return Response(PrefSer(p).data)


class Inbox(LoginRequiredMixin, TemplateView):
    template_name = "notifications/inbox.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notifications"] = (
            Notification.objects.filter(user=self.request.user)[:50]
        )
        ctx["unread"] = unread_count(self.request.user)
        return ctx


router = DefaultRouter()
router.register(r"notifications", NotifVS, basename="notification")

urlpatterns = [
    path("", Inbox.as_view(), name="inbox"),
    path("api/", include(router.urls)),
    path("api/unread/", unread, name="unread"),
    path("api/preferences/", prefs, name="preferences"),
]
