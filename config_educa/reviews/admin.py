from django.contrib import admin
from .models import CourseReview, ReviewHelpful


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ['course', 'user', 'rating', 'is_verified_purchase', 'helpful_count', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['course__title', 'user__username', 'review_text']
    readonly_fields = ['created_at', 'updated_at', 'is_verified_purchase']
    date_hierarchy = 'created_at'


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['review__course__title', 'user__username']
