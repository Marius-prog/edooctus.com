from django.test import TestCase
from django.contrib.auth.models import User
from courses.models import Course, Subject
from .models import CourseReview, ReviewHelpful


class CourseReviewModelTest(TestCase):
    """Test CourseReview model"""

    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.subject = Subject.objects.create(title='Test Subject', slug='test-subject')
        self.course = Course.objects.create(
            owner=self.user,
            subject=self.subject,
            title='Test Course',
            slug='test-course',
            overview='Test course overview'
        )

    def test_create_review(self):
        """Test creating a course review"""
        review = CourseReview.objects.create(
            course=self.course,
            user=self.user,
            rating=5,
            title='Great Course',
            review_text='This course was excellent!'
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.title, 'Great Course')
        self.assertTrue(str(review).startswith('testuser'))

    def test_auto_verify_enrolled_student(self):
        """Test that reviews auto-verify for enrolled students"""
        # Enroll the user
        self.course.students.add(self.user)

        review = CourseReview.objects.create(
            course=self.course,
            user=self.user,
            rating=4,
            review_text='Good course'
        )
        self.assertTrue(review.is_verified_purchase)

    def test_unique_review_per_user_course(self):
        """Test that each user can only have one review per course"""
        CourseReview.objects.create(
            course=self.course,
            user=self.user,
            rating=5,
            review_text='First review'
        )

        # Attempting to create another review should fail
        with self.assertRaises(Exception):
            CourseReview.objects.create(
                course=self.course,
                user=self.user,
                rating=3,
                review_text='Second review'
            )

    def test_course_rating_update(self):
        """Test that course rating updates when reviews are added"""
        self.assertEqual(self.course.total_reviews, 0)
        self.assertEqual(self.course.average_rating, 0)

        # Create reviews
        user2 = User.objects.create_user(username='user2', password='pass123')
        CourseReview.objects.create(
            course=self.course,
            user=self.user,
            rating=5,
            review_text='Excellent!'
        )
        CourseReview.objects.create(
            course=self.course,
            user=user2,
            rating=3,
            review_text='Good'
        )

        # Refresh from database
        self.course.refresh_from_db()
        self.assertEqual(self.course.total_reviews, 2)
        self.assertEqual(self.course.average_rating, 4.00)


class ReviewHelpfulTest(TestCase):
    """Test ReviewHelpful model"""

    def setUp(self):
        """Create test data"""
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.subject = Subject.objects.create(title='Test Subject', slug='test-subject')
        self.course = Course.objects.create(
            owner=self.user1,
            subject=self.subject,
            title='Test Course',
            slug='test-course',
            overview='Test overview'
        )
        self.review = CourseReview.objects.create(
            course=self.course,
            user=self.user1,
            rating=5,
            review_text='Great!'
        )

    def test_mark_review_helpful(self):
        """Test marking a review as helpful"""
        helpful = ReviewHelpful.objects.create(
            review=self.review,
            user=self.user2
        )
        self.assertEqual(helpful.review, self.review)
        self.assertEqual(helpful.user, self.user2)

    def test_unique_helpful_per_user_review(self):
        """Test that each user can only mark a review helpful once"""
        ReviewHelpful.objects.create(
            review=self.review,
            user=self.user2
        )

        # Second attempt should fail
        with self.assertRaises(Exception):
            ReviewHelpful.objects.create(
                review=self.review,
                user=self.user2
            )
