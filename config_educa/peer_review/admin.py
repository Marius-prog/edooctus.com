from django.contrib import admin
from .models import Assignment, Submission, PeerReview


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "is_published", "peer_reviews_required", "due_at")
    list_filter = ("is_published", "course")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("author", "assignment", "status", "avg_score", "review_count")
    list_filter = ("status",)


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = ("submission", "reviewer", "score", "is_anonymous", "created")
    list_filter = ("is_anonymous",)
