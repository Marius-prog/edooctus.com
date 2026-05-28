# Review System Installation Guide

## Overview

A complete course review and rating system has been implemented for the Educto platform. This guide covers the installation and testing steps.

## What Was Implemented

### 1. New Django App: `reviews`
Located in: `/config_educa/reviews/`

**Files created:**
- `__init__.py` - Package initialization
- `apps.py` - App configuration
- `models.py` - CourseReview and ReviewHelpful models
- `forms.py` - CourseReviewForm
- `views.py` - add_review and mark_helpful views
- `admin.py` - Admin interface configuration
- `urls.py` - URL routing
- `tests.py` - Unit tests
- `templates/reviews/add_review.html` - Review form template
- `README.md` - Detailed documentation

### 2. Course Model Updates
File: `/config_educa/courses/models.py`

**Added fields:**
- `average_rating` - Decimal field (0-5, 2 decimal places)
- `total_reviews` - Integer field

**Added method:**
- `update_rating()` - Calculates and updates average rating

### 3. Configuration Updates

**Settings** (`config_educa/settings/base.py`):
- Added `'reviews.apps.ReviewsConfig'` to INSTALLED_APPS

**URLs** (`config_educa/urls.py`):
- Added `path('reviews/', include('reviews.urls', namespace='reviews'))`

## Installation Steps

### Step 1: Create Database Migrations

```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio/config_educa

# Activate virtual environment (if using venv)
source ../venv/bin/activate

# Create migrations for reviews app
python manage.py makemigrations reviews

# Create migrations for updated Course model
python manage.py makemigrations courses

# Review migration files
python manage.py showmigrations

# Apply migrations
python manage.py migrate
```

### Step 2: Verify Installation

```bash
# Run Django checks
python manage.py check

# Run tests
python manage.py test reviews

# Start development server
python manage.py runserver
```

### Step 3: Test in Browser

1. **Login to admin** at `http://localhost:8000/(K+J+u.dt8/`
2. **Navigate to Reviews** section
3. **Verify models** are registered:
   - Course Reviews
   - Review Helpful Votes

### Step 4: Integration with Course Templates

Update the course detail template to show reviews:

**File:** `config_educa/courses/templates/courses/course/detail.html`

Add this code where you want to display reviews:

```django
<!-- Course Rating Summary -->
{% if course.total_reviews > 0 %}
<div class="rating-summary">
  <h3>Student Reviews</h3>
  <div class="rating-overview">
    <span class="rating-stars">
      {% with rating=course.average_rating|floatformat:0|add:"0" %}
        {% for i in "12345" %}
          {% if forloop.counter <= rating %}
            <span class="star filled">⭐</span>
          {% else %}
            <span class="star">☆</span>
          {% endif %}
        {% endfor %}
      {% endwith %}
    </span>
    <span class="rating-text">
      {{ course.average_rating|floatformat:1 }} out of 5 ({{ course.total_reviews }} review{{ course.total_reviews|pluralize }})
    </span>
  </div>
</div>
{% endif %}

<!-- Write Review Button (for enrolled students only) -->
{% if request.user.is_authenticated and request.user in course.students.all %}
<div class="review-actions">
  <a href="{% url 'reviews:add_review' course.id %}" class="btn btn-primary">
    Write a Review
  </a>
</div>
{% endif %}

<!-- Reviews List -->
<div class="reviews-list">
  <h4>Student Reviews ({{ course.total_reviews }})</h4>
  {% for review in course.reviews.all %}
  <div class="review-item">
    <div class="review-header">
      <div class="reviewer-info">
        <strong>{{ review.user.username }}</strong>
        {% if review.is_verified_purchase %}
          <span class="badge badge-success">Verified Student</span>
        {% endif %}
      </div>
      <div class="review-rating">
        {% for i in "12345" %}
          {% if forloop.counter <= review.rating %}⭐{% else %}☆{% endif %}
        {% endfor %}
      </div>
    </div>

    {% if review.title %}
    <h5 class="review-title">{{ review.title }}</h5>
    {% endif %}

    <p class="review-text">{{ review.review_text }}</p>

    <div class="review-footer">
      <span class="review-date">{{ review.created_at|date:"F d, Y" }}</span>
      {% if request.user.is_authenticated %}
      <form method="post" action="{% url 'reviews:mark_helpful' review.id %}" style="display:inline;">
        {% csrf_token %}
        <button type="submit" class="btn-link">
          👍 Helpful ({{ review.helpful_count }})
        </button>
      </form>
      {% endif %}
    </div>
  </div>
  {% empty %}
  <p class="no-reviews">No reviews yet. Be the first to review this course!</p>
  {% endfor %}
</div>
```

## Features

### 1. Course Reviews
- Students can leave 1-5 star ratings
- Optional review title
- Required review text
- Auto-verified if student is enrolled
- One review per student per course
- Edit existing reviews

### 2. Helpful Voting
- Students can mark reviews as helpful
- Toggle functionality (mark/unmark)
- Helpful count displayed
- Unique vote per user per review

### 3. Course Rating
- Automatic average calculation
- Updates on every review save
- Displayed with total review count
- Used for course rankings

### 4. Admin Interface
- Moderate reviews
- Filter by rating, verification, date
- Search by course, user, content
- View helpful votes
- Read-only timestamps

## URLs

### Public URLs
- `/reviews/add/<course_id>/` - Add/edit review (login required, enrollment required)
- `/reviews/helpful/<review_id>/` - Mark review helpful (login required)

### Admin URLs
- `/(K+J+u.dt8/reviews/coursereview/` - Manage reviews
- `/(K+J+u.dt8/reviews/reviewhelpful/` - Manage helpful votes

## Models

### CourseReview
```python
- course (FK to Course)
- user (FK to User)
- rating (1-5 integer)
- title (optional string)
- review_text (required text)
- is_verified_purchase (auto-set boolean)
- helpful_count (integer)
- created_at, updated_at (timestamps)
```

**Constraints:**
- Unique: (course, user)
- Indexes: course+date, rating, helpful_count

### ReviewHelpful
```python
- review (FK to CourseReview)
- user (FK to User)
- created_at (timestamp)
```

**Constraints:**
- Unique: (review, user)

### Course (updated)
```python
- average_rating (Decimal 0-5)
- total_reviews (Integer)
- update_rating() method
```

## Testing

Run the test suite:

```bash
python manage.py test reviews

# Expected tests:
# - test_create_review
# - test_auto_verify_enrolled_student
# - test_unique_review_per_user_course
# - test_course_rating_update
# - test_mark_review_helpful
# - test_unique_helpful_per_user_review
```

## Docker Deployment

If using Docker:

```bash
# Build containers
docker-compose build

# Run migrations
docker-compose exec web python config_educa/manage.py makemigrations
docker-compose exec web python config_educa/manage.py migrate

# Run tests
docker-compose exec web python config_educa/manage.py test reviews

# Restart services
docker-compose restart web
```

## Common Issues

### Issue: Migration conflicts
**Solution:** Run `python manage.py makemigrations --merge`

### Issue: "No such table: reviews_coursereview"
**Solution:** Run migrations: `python manage.py migrate`

### Issue: "You must be enrolled to leave a review"
**Solution:** Enroll the user in the course first via admin or students app

### Issue: Can't mark review as helpful
**Solution:** Ensure user is logged in

## Next Steps

1. ✅ Run migrations
2. ✅ Test in admin interface
3. ✅ Update course detail template
4. ✅ Add CSS styling for reviews
5. ✅ Test review submission
6. ✅ Test helpful voting
7. ⏹️ Add review API endpoints (optional)
8. ⏹️ Add review notifications (optional)
9. ⏹️ Add review analytics (optional)

## Files Modified

### Created
- `/config_educa/reviews/` (entire app directory)
- `/REVIEW_SYSTEM_INSTALLATION.md` (this file)

### Modified
- `/config_educa/courses/models.py` (added rating fields and method)
- `/config_educa/config_educa/settings/base.py` (added reviews to INSTALLED_APPS)
- `/config_educa/config_educa/urls.py` (added reviews URL routing)

## Support

For detailed documentation, see:
- `/config_educa/reviews/README.md` - Complete feature documentation
- `/config_educa/reviews/tests.py` - Test examples
- `/config_educa/reviews/views.py` - View implementation

## Success Criteria

System is successfully installed when:
- ✅ Migrations run without errors
- ✅ Tests pass
- ✅ Reviews visible in admin
- ✅ Students can submit reviews
- ✅ Course ratings update automatically
- ✅ Helpful voting works
- ✅ Reviews display on course pages
