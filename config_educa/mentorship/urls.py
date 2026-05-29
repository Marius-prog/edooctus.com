from django.urls import path, include
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from shared.permissions import IsOwnerOrReadOnly
from .models import MentorProfile, MentorshipRequest, MentorshipSession, find_mentors

app_name = "mentorship"


class MentorProfileSer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        fields = ["id", "user", "bio", "expertise", "timezone_name",
                  "max_active_mentees", "is_accepting", "avg_rating", "total_sessions"]
        read_only_fields = ["user", "avg_rating", "total_sessions"]


class RequestSer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipRequest
        fields = ["id", "mentee", "mentor", "message", "goals", "status",
                  "created", "responded_at", "ended_at"]
        read_only_fields = ["mentee", "status", "created", "responded_at", "ended_at"]


class SessionSer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = ["id", "pairing", "scheduled_at", "duration_minutes",
                  "notes", "mentor_rating", "mentee_rating", "completed"]


class MentorProfileVS(viewsets.ModelViewSet):
    queryset = MentorProfile.objects.select_related("user")
    serializer_class = MentorProfileSer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RequestVS(viewsets.ModelViewSet):
    serializer_class = RequestSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        u = self.request.user
        return MentorshipRequest.objects.filter(mentor=u) | MentorshipRequest.objects.filter(mentee=u)

    def perform_create(self, serializer):
        serializer.save(mentee=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        r = self.get_object()
        if r.mentor_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        r.accept()
        return Response(RequestSer(r).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        r = self.get_object()
        if r.mentor_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        r.decline()
        return Response(RequestSer(r).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        r = self.get_object()
        if request.user.id not in (r.mentor_id, r.mentee_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        r.end()
        return Response(RequestSer(r).data)


class SessionVS(viewsets.ModelViewSet):
    serializer_class = SessionSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        u = self.request.user
        return MentorshipSession.objects.filter(
            pairing__mentor=u
        ) | MentorshipSession.objects.filter(pairing__mentee=u)

    def perform_create(self, serializer):
        pairing = serializer.validated_data["pairing"]
        if self.request.user.id not in (pairing.mentor_id, pairing.mentee_id):
            raise PermissionDenied("You are not a participant in this pairing.")
        serializer.save()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def match(request):
    tags = request.GET.getlist("tag")
    limit = int(request.GET.get("limit", 5))
    matches = find_mentors(tags, limit=limit)
    return Response(MentorProfileSer(matches, many=True).data)


class Hub(LoginRequiredMixin, TemplateView):
    template_name = "mentorship/hub.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        ctx["mentors"] = MentorProfile.objects.filter(
            is_accepting=True,
        ).select_related("user")[:20]
        ctx["my_outgoing"] = MentorshipRequest.objects.filter(
            mentee=u,
        ).select_related("mentor")
        ctx["my_incoming"] = MentorshipRequest.objects.filter(
            mentor=u,
        ).select_related("mentee")
        return ctx


router = DefaultRouter()
router.register(r"mentors", MentorProfileVS, basename="mentor")
router.register(r"requests", RequestVS, basename="request")
router.register(r"sessions", SessionVS, basename="session")

urlpatterns = [
    path("", Hub.as_view(), name="hub"),
    path("api/", include(router.urls)),
    path("api/match/", match, name="match"),
]
