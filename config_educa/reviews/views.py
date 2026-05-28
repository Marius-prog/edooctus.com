from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from courses.models import Course
from .models import CourseReview, ReviewHelpful
from .forms import CourseReviewForm


@login_required
def add_review(request, course_id):
    """Add or update a course review"""
    course = get_object_or_404(Course, id=course_id)

    # Check if user is enrolled
    if not course.students.filter(id=request.user.id).exists():
        messages.error(request, 'You must be enrolled in this course to leave a review.')
        return redirect('course_detail', slug=course.slug)

    # Get existing review or create new
    review, created = CourseReview.objects.get_or_create(
        course=course,
        user=request.user
    )

    if request.method == 'POST':
        form = CourseReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your review has been saved!')
            return redirect('course_detail', slug=course.slug)
    else:
        form = CourseReviewForm(instance=review)

    return render(request, 'reviews/add_review.html', {
        'form': form,
        'course': course,
        'is_edit': not created
    })


@login_required
def mark_helpful(request, review_id):
    """Mark a review as helpful"""
    review = get_object_or_404(CourseReview, id=review_id)

    helpful, created = ReviewHelpful.objects.get_or_create(
        review=review,
        user=request.user
    )

    if not created:
        # User already marked it, so unmark
        helpful.delete()
        review.helpful_count = max(0, review.helpful_count - 1)
        messages.info(request, 'Removed helpful vote')
    else:
        review.helpful_count += 1
        messages.success(request, 'Marked as helpful!')

    review.save(update_fields=['helpful_count'])
    return redirect('course_detail', slug=review.course.slug)
