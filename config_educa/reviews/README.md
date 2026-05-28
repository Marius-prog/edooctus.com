# Course Reviews App

## Overview

A complete review and rating system for courses in the Educto platform. Students can leave reviews, rate courses (1-5 stars), and mark helpful reviews.

## Features

- ⭐ Star ratings (1-5) for courses
- ✍️ Written reviews with optional title
- ✅ Auto-verification for enrolled students
- 👍 "Helpful" voting system for reviews
- 📊 Automatic course rating aggregation
- 🔒 One review per student per course
- 🛡️ Admin moderation interface

## Models

### CourseReview
- `course` - ForeignKey to Course
- `user` - ForeignKey to User
- `rating` - Integer (1-5)
- `title` - Optional review title
- `review_text` - Full review content
- `is_verified_purchase` - Auto-set if student is enrolled
- `helpful_count` - Number of helpful votes
- `created_at` / `updated_at` - Timestamps

**Constraints:**
- Unique together: (course, user)
- Indexed on: course, rating, helpful_count

### ReviewHelpful
- `review` - ForeignKey to CourseReview
- `user` - ForeignKey to User
- `created_at` - Timestamp

**Constraints:**
- Unique together: (review, user)

## Course Model Extensions

Two new fields added to the Course model:
- `average_rating` - Decimal (0-5, 2 decimal places)
- `total_reviews` - Integer

Method added:
- `update_rating()` - Recalculates average rating and review count

## Views

### add_review(request, course_id)
- **URL:** `/reviews/add/<course_id>/`
- **Auth:** Login required
- **Features:**
  - Checks enrollment before allowing review
  - Creates new or updates existing review
  - Redirects to course detail on success
  - Shows success/error messages

### mark_helpful(request, review_id)
- **URL:** `/reviews/helpful/<review_id>/`
- **Auth:** Login required
- **Features:**
  - Toggles helpful vote (add/remove)
  - Updates helpful_count
  - Redirects to course detail

## Forms

### CourseReviewForm
- Fields: rating, title, review_text
- Radio buttons for star rating
- Bootstrap-styled inputs
- Textarea for review text

## Admin Interface

### CourseReviewAdmin
- List display: course, user, rating, verification, helpful count, date
- Filters: rating, verification status, created date
- Search: course title, username, review text
- Date hierarchy for easy browsing

### ReviewHelpfulAdmin
- List display: review, user, date
- Filters: created date
- Search: course title, username

## URL Routing

In `config_educa/urls.py`:
```python
path('reviews/', include('reviews.urls', namespace='reviews')),
```

## Installation Steps

### 1. Run Migrations
```bash
cd config_educa
python manage.py makemigrations reviews
python manage.py makemigrations courses  # For new Course fields
python manage.py migrate
```

### 2. Update Templates

Add review section to course detail template (`courses/templates/courses/course/detail.html`):

```django
<!-- Course Rating Display -->
{% if course.total_reviews > 0 %}
<div class="course-rating">
  <span class="rating-stars">
    {% for i in "12345" %}
      {% if forloop.counter <= course.average_rating %}⭐{% endif %}
    {% endfor %}
  </span>
  <span class="rating-text">
    {{ course.average_rating|floatformat:1 }} ({{ course.total_reviews }} review{{ course.total_reviews|pluralize }})
  </span>
</div>
{% endif %}

<!-- Add Review Button (for enrolled students) -->
{% if user in course.students.all %}
<a href="{% url 'reviews:add_review' course.id %}" class="btn btn-primary">
  Write a Review
</a>
{% endif %}

<!-- Reviews List -->
<h3>Student Reviews</h3>
{% for review in course.reviews.all %}
<div class="review">
  <div class="review-header">
    <strong>{{ review.user.username }}</strong>
    <span class="rating">{{ review.rating }}⭐</span>
    {% if review.is_verified_purchase %}
      <span class="badge">Verified Student</span>
    {% endif %}
  </div>
  {% if review.title %}
    <h4>{{ review.title }}</h4>
  {% endif %}
  <p>{{ review.review_text }}</p>
  <div class="review-footer">
    <span>{{ review.created_at|date:"M d, Y" }}</span>
    <form method="post" action="{% url 'reviews:mark_helpful' review.id %}" style="display:inline;">
      {% csrf_token %}
      <button type="submit" class="btn-link">
        👍 Helpful ({{ review.helpful_count }})
      </button>
    </form>
  </div>
</div>
{% empty %}
<p>No reviews yet. Be the first to review this course!</p>
{% endfor %}
```

## Testing

Run tests:
```bash
python manage.py test reviews
```

Test coverage:
- Create review
- Auto-verification for enrolled students
- Unique constraint (one review per user per course)
- Course rating updates
- Helpful voting
- Unique helpful constraint

## Usage Examples

### Check if user has reviewed a course
```python
has_reviewed = CourseReview.objects.filter(
    course=course,
    user=request.user
).exists()
```

### Get top-rated courses
```python
top_courses = Course.objects.filter(
    total_reviews__gt=0
).order_by('-average_rating', '-total_reviews')[:10]
```

### Get most helpful reviews
```python
helpful_reviews = CourseReview.objects.filter(
    course=course
).order_by('-helpful_count', '-created_at')[:5]
```

### Recalculate all course ratings
```python
for course in Course.objects.all():
    course.update_rating()
```

## Security Considerations

- ✅ Login required for all review actions
- ✅ Enrollment check before allowing reviews
- ✅ Unique constraints prevent spam
- ✅ Admin moderation available
- ✅ CSRF protection on all forms
- ✅ Read-only fields in admin (timestamps, verification)

## Performance Notes

- Database indexes on common queries:
  - course + created_at (recent reviews)
  - rating (filter by rating)
  - helpful_count (most helpful)
- Use `select_related('user')` when querying reviews
- Consider caching course rating displays

## Future Enhancements

Potential additions:
- Review images/attachments
- Review responses from instructors
- Flag/report inappropriate reviews
- Review editing history
- Email notifications for new reviews
- Review analytics dashboard
- Sentiment analysis
- Review templates/prompts

## Migration Files

After running makemigrations, you'll get:
- `reviews/migrations/0001_initial.py` - Creates CourseReview and ReviewHelpful models
- `courses/migrations/XXXX_add_rating_fields.py` - Adds average_rating and total_reviews to Course

## API Integration (Future)

If adding to REST API:
```python
# In courses/api/serializers.py
class CourseSerializer(serializers.ModelSerializer):
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [..., 'average_rating', 'total_reviews']
```

## Support

For issues or questions about the review system, check:
1. Django admin logs for moderation
2. Database constraints for integrity errors
3. User enrollment status for permission errors
4. Course model for rating calculation issues
