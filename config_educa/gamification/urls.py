from django.urls import path, include
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import Badge, UserBadge, user_points, leaderboard

app_name = "gamification"


class BadgeSer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ["id", "name", "slug", "description", "icon", "points_reward", "rule_code"]


class UserBadgeSer(serializers.ModelSerializer):
    badge = BadgeSer(read_only=True)
    class Meta:
        model = UserBadge
        fields = ["id", "badge", "awarded_at", "awarded_for"]


class BadgeVS(viewsets.ReadOnlyModelViewSet):
    queryset = Badge.objects.filter(is_active=True)
    serializer_class = BadgeSer
    permission_classes = [permissions.IsAuthenticated]


class MyBadgesVS(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserBadgeSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user).select_related("badge")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def leaderboard_view(request):
    limit = int(request.GET.get("limit", 10))
    return Response({"leaderboard": list(leaderboard(limit=limit))})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_points(request):
    return Response({"points": user_points(request.user)})


class BadgesPage(LoginRequiredMixin, TemplateView):
    template_name = "gamification/badges.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from .models import Badge, UserBadge
        earned_ids = set(UserBadge.objects.filter(user=self.request.user)
                         .values_list("badge_id", flat=True))
        ctx["all_badges"] = Badge.objects.filter(is_active=True)
        ctx["earned_ids"] = earned_ids
        ctx["my_points"] = user_points(self.request.user)
        ctx["leaderboard"] = list(leaderboard(limit=10))
        return ctx


router = DefaultRouter()
router.register(r"badges", BadgeVS, basename="badge")
router.register(r"my-badges", MyBadgesVS, basename="my-badge")

urlpatterns = [
    path("", BadgesPage.as_view(), name="badges"),
    path("api/", include(router.urls)),
    path("api/leaderboard/", leaderboard_view, name="leaderboard"),
    path("api/points/", my_points, name="points"),
]
