from django.urls import path, include
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from .models import Assignment, Submission, PeerReview

app_name = "peer_review"


class AssignmentSer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "course", "title", "instructions", "rubric",
                  "due_at", "peer_reviews_required", "is_published", "created"]


class SubmissionSer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ["id", "assignment", "author", "content", "file",
                  "status", "submitted_at", "avg_score", "review_count"]
        read_only_fields = ["author", "status", "submitted_at", "avg_score", "review_count"]


class PeerReviewSer(serializers.ModelSerializer):
    class Meta:
        model = PeerReview
        fields = ["id", "submission", "reviewer", "score", "feedback",
                  "is_anonymous", "created"]
        read_only_fields = ["reviewer", "created"]


class AssignmentVS(viewsets.ReadOnlyModelViewSet):
    queryset = Assignment.objects.filter(is_published=True)
    serializer_class = AssignmentSer
    permission_classes = [permissions.IsAuthenticated]


class SubmissionVS(viewsets.ModelViewSet):
    serializer_class = SubmissionSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Submission.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def submit_for_review(self, request, pk=None):
        s = self.get_object()
        s.submit()
        return Response(SubmissionSer(s).data)


class PeerReviewVS(viewsets.ModelViewSet):
    serializer_class = PeerReviewSer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return PeerReview.objects.filter(reviewer=self.request.user)

    def perform_create(self, serializer):
        submission = serializer.validated_data["submission"]
        if submission.author_id == self.request.user.id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You cannot review your own submission.")
        serializer.save(reviewer=self.request.user)


class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = "peer_review/list.html"


class AssignmentDetailView(LoginRequiredMixin, DetailView):
    model = Assignment
    template_name = "peer_review/detail.html"


router = DefaultRouter()
router.register(r"assignments", AssignmentVS, basename="assignment")
router.register(r"submissions", SubmissionVS, basename="submission")
router.register(r"reviews", PeerReviewVS, basename="review")

urlpatterns = [
    path("", AssignmentListView.as_view(), name="list"),
    path("<int:pk>/", AssignmentDetailView.as_view(), name="detail"),
    path("api/", include(router.urls)),
]
