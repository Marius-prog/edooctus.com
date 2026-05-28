from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from courses.models import Course


class CourseReview(models.Model):
    """Student review and rating for a course"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200, blank=True)
    review_text = models.TextField(help_text="Share your experience with this course")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified_purchase = models.BooleanField(default=False, help_text="Student is enrolled in this course")
    helpful_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ['course', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course', '-created_at']),
            models.Index(fields=['rating']),
            models.Index(fields=['-helpful_count']),
        ]
        verbose_name = 'Course Review'
        verbose_name_plural = 'Course Reviews'

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.rating}★)"

    def save(self, *args, **kwargs):
        """Auto-verify if user is enrolled"""
        if self.course.students.filter(id=self.user.id).exists():
            self.is_verified_purchase = True
        super().save(*args, **kwargs)
        # Update course average rating
        self.course.update_rating()


class ReviewHelpful(models.Model):
    """Track which users found a review helpful"""
    review = models.ForeignKey(CourseReview, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['review', 'user']
        verbose_name = 'Review Helpful Vote'
        verbose_name_plural = 'Review Helpful Votes'

    def __str__(self):
        return f"{self.user.username} found review helpful"
