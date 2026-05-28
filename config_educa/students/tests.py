from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from courses.models import Course, Subject, Module
from students.forms import CourseEnrollForm


class DashboardViewTest(TestCase):
    """Foundry dashboard view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="dashstudent", password="pw12345!")
        self.url = reverse("dashboard")

    def test_redirects_when_anonymous(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_renders_for_authenticated_user_with_no_data(self):
        self.client.login(username="dashstudent", password="pw12345!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/dashboard.html")
        self.assertContains(response, "MY LEARNING")
        self.assertContains(response, "CONTINUE LEARNING")
        self.assertContains(response, "ACTIVITY")
        self.assertContains(response, "RECOMMENDED FOR YOU")

    def test_metrics_present_in_context(self):
        self.client.login(username="dashstudent", password="pw12345!")
        response = self.client.get(self.url)
        self.assertIn("metric_enrolled", response.context)
        self.assertIn("metric_completed", response.context)
        self.assertIn("metric_streak", response.context)
        self.assertIn("continue_learning", response.context)
        self.assertIn("activity_bars", response.context)
        self.assertIn("recommended", response.context)


class StudentRegistrationTest(TestCase):
    """Test student registration functionality"""

    def setUp(self):
        self.client = Client()
        self.registration_url = reverse('student_registration')

    def test_registration_page_loads(self):
        """Test registration page is accessible"""
        response = self.client.get(self.registration_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'students/student/registration.html')

    def test_successful_registration(self):
        """Test user can register successfully"""
        data = {
            'username': 'newstudent',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }

        response = self.client.post(self.registration_url, data)

        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)

        # User should be created
        user = User.objects.filter(username='newstudent').first()
        self.assertIsNotNone(user)

        # Verify redirect goes to student course list
        self.assertRedirects(response, reverse('student_course_list'))

    def test_registration_auto_login(self):
        """Test user is automatically logged in after registration"""
        data = {
            'username': 'autologinuser',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }

        response = self.client.post(self.registration_url, data, follow=True)

        # Check user is logged in by accessing authenticated view
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, 'autologinuser')

    def test_registration_password_mismatch(self):
        """Test registration fails with mismatched passwords"""
        data = {
            'username': 'badpassuser',
            'password1': 'TestPassword123!',
            'password2': 'DifferentPassword456!',
        }

        response = self.client.post(self.registration_url, data)

        # Should stay on registration page
        self.assertEqual(response.status_code, 200)

        # User should not be created
        user = User.objects.filter(username='badpassuser').first()
        self.assertIsNone(user)


class CourseEnrollmentTest(TestCase):
    """Test course enrollment functionality"""

    @classmethod
    def setUpTestData(cls):
        # Create instructor
        cls.instructor = User.objects.create_user(
            username='instructor',
            password='instructorpass'
        )

        # Create student
        cls.student = User.objects.create_user(
            username='student',
            password='studentpass'
        )

        # Create subject and course
        cls.subject = Subject.objects.create(
            title='Mathematics',
            slug='mathematics'
        )

        cls.course = Course.objects.create(
            owner=cls.instructor,
            subject=cls.subject,
            title='Algebra 101',
            slug='algebra-101',
            overview='Learn algebra basics'
        )

    def setUp(self):
        self.client = Client()

    def test_successful_enrollment(self):
        """Test student can enroll in a course"""
        self.client.login(username='student', password='studentpass')

        enroll_url = reverse('student_enroll_course')
        response = self.client.post(enroll_url, {
            'course': self.course.id
        })

        # Should redirect after enrollment
        self.assertEqual(response.status_code, 302)

        # Student should be enrolled
        self.assertTrue(
            self.course.students.filter(id=self.student.id).exists()
        )

    def test_enrollment_requires_login(self):
        """Test enrollment requires authentication"""
        enroll_url = reverse('student_enroll_course')
        response = self.client.post(enroll_url, {
            'course': self.course.id
        })

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

        # Student should not be enrolled
        self.assertFalse(
            self.course.students.filter(id=self.student.id).exists()
        )

    def test_duplicate_enrollment_prevented(self):
        """Test student cannot enroll twice in same course"""
        self.client.login(username='student', password='studentpass')

        # Enroll once
        self.course.students.add(self.student)

        enroll_url = reverse('student_enroll_course')
        response = self.client.post(enroll_url, {
            'course': self.course.id
        })

        # Should still redirect (Django handles duplicates silently with M2M)
        self.assertEqual(response.status_code, 302)

        # Should only be enrolled once
        enrollment_count = self.course.students.filter(id=self.student.id).count()
        self.assertEqual(enrollment_count, 1)

    def test_enrollment_redirects_to_course_detail(self):
        """Test enrollment redirects to course detail page"""
        self.client.login(username='student', password='studentpass')

        enroll_url = reverse('student_enroll_course')
        response = self.client.post(enroll_url, {
            'course': self.course.id
        }, follow=True)

        # Should end up on course detail page
        expected_url = reverse('student_course_detail', args=[self.course.id])
        self.assertRedirects(response, expected_url)


class StudentCourseListTest(TestCase):
    """Test student course listing functionality"""

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username='student',
            password='studentpass'
        )

        cls.instructor = User.objects.create_user(
            username='instructor',
            password='instructorpass'
        )

        cls.subject = Subject.objects.create(
            title='Science',
            slug='science'
        )

        # Create multiple courses
        cls.enrolled_course = Course.objects.create(
            owner=cls.instructor,
            subject=cls.subject,
            title='Biology 101',
            slug='biology-101',
            overview='Study of life'
        )

        cls.not_enrolled_course = Course.objects.create(
            owner=cls.instructor,
            subject=cls.subject,
            title='Chemistry 101',
            slug='chemistry-101',
            overview='Study of matter'
        )

        # Enroll student in first course
        cls.enrolled_course.students.add(cls.student)

    def setUp(self):
        self.client = Client()

    def test_course_list_requires_login(self):
        """Test course list requires authentication"""
        url = reverse('student_course_list')
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_course_list_shows_only_enrolled_courses(self):
        """Test student only sees courses they're enrolled in"""
        self.client.login(username='student', password='studentpass')

        url = reverse('student_course_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Should show enrolled course
        self.assertContains(response, 'Biology 101')

        # Should NOT show non-enrolled course
        self.assertNotContains(response, 'Chemistry 101')

    def test_course_list_uses_select_related(self):
        """Test query optimization with select_related"""
        self.client.login(username='student', password='studentpass')

        url = reverse('student_course_list')

        # The view uses select_related, so accessing related objects
        # should not cause additional queries
        with self.assertNumQueries(6):  # Should be minimal queries
            response = self.client.get(url)
            # Accessing related objects shouldn't cause additional queries
            for course in response.context['object_list']:
                _ = course.owner.username
                _ = course.subject.title


class StudentCourseDetailTest(TestCase):
    """Test student course detail functionality"""

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username='student',
            password='studentpass'
        )

        cls.instructor = User.objects.create_user(
            username='instructor',
            password='instructorpass'
        )

        cls.subject = Subject.objects.create(title='Math', slug='math')

        cls.course = Course.objects.create(
            owner=cls.instructor,
            subject=cls.subject,
            title='Calculus',
            slug='calculus',
            overview='Study of change'
        )

        # Create modules
        cls.module1 = Module.objects.create(
            course=cls.course,
            title='Module 1: Limits',
            description='Introduction to limits'
        )

        cls.module2 = Module.objects.create(
            course=cls.course,
            title='Module 2: Derivatives',
            description='Understanding derivatives'
        )

        # Enroll student
        cls.course.students.add(cls.student)

    def setUp(self):
        self.client = Client()

    def test_course_detail_requires_enrollment(self):
        """Test only enrolled students can access course detail"""
        # Create non-enrolled user
        other_user = User.objects.create_user(
            username='other',
            password='otherpass'
        )

        self.client.login(username='other', password='otherpass')

        url = reverse('student_course_detail', args=[self.course.id])
        response = self.client.get(url)

        # Should get 404 (not enrolled)
        self.assertEqual(response.status_code, 404)

    def test_course_detail_shows_modules(self):
        """Test course detail displays all modules"""
        self.client.login(username='student', password='studentpass')

        url = reverse('student_course_detail', args=[self.course.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Module 1: Limits')
        self.assertContains(response, 'Module 2: Derivatives')

    def test_course_detail_displays_first_module_by_default(self):
        """Test first module is shown when no specific module requested"""
        self.client.login(username='student', password='studentpass')

        url = reverse('student_course_detail', args=[self.course.id])
        response = self.client.get(url)

        # First module should be in context
        self.assertEqual(response.context['module'], self.module1)

    def test_course_detail_with_specific_module(self):
        """Test specific module can be requested"""
        self.client.login(username='student', password='studentpass')

        url = reverse('student_course_detail_module', args=[self.course.id, self.module2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['module'], self.module2)

    def test_course_detail_prefetches_contents(self):
        """Test query optimization with prefetch_related"""
        self.client.login(username='student', password='studentpass')

        url = reverse('student_course_detail', args=[self.course.id])

        # Should use minimal queries
        with self.assertNumQueries(6):  # Optimized with prefetch
            response = self.client.get(url)
            course = response.context['object']
            # Accessing modules shouldn't cause N+1 queries
            for module in course.modules.all():
                _ = module.title


class CourseEnrollFormTest(TestCase):
    """Test CourseEnrollForm"""

    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(username='instructor', password='pass')
        cls.subject = Subject.objects.create(title='Subject', slug='subject')
        cls.course = Course.objects.create(
            owner=cls.instructor,
            subject=cls.subject,
            title='Course',
            slug='course',
            overview='Overview'
        )

    def test_form_valid_with_course(self):
        """Test form is valid with course"""
        form = CourseEnrollForm(data={'course': self.course.id})
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_course(self):
        """Test form is invalid without course"""
        form = CourseEnrollForm(data={})
        self.assertFalse(form.is_valid())

    def test_form_invalid_with_nonexistent_course(self):
        """Test form is invalid with non-existent course ID"""
        form = CourseEnrollForm(data={'course': 99999})
        self.assertFalse(form.is_valid())


from django.test import override_settings
from courses.models import Content, Text
from django.contrib.contenttypes.models import ContentType


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class PlayerHtmxTests(TestCase):
    """M4: Foundry course player — HTMX content swap + mark-complete endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="playerstu", password="pw12345!")
        cls.owner = User.objects.create_user(username="playerinstr", password="pw12345!")
        cls.subject = Subject.objects.create(title="Tests", slug="m4-tests")
        cls.course = Course.objects.create(
            owner=cls.owner, subject=cls.subject,
            title="M4 Course", slug="m4-course", overview="player tests",
        )
        cls.course.students.add(cls.user)
        cls.module = Module.objects.create(course=cls.course, title="M4 Module", description="d")
        text_item = Text.objects.create(owner=cls.owner, title="Lesson 1", content="Hello world")
        cls.content = Content.objects.create(
            module=cls.module,
            content_type=ContentType.objects.get_for_model(Text),
            object_id=text_item.id,
        )

    def setUp(self):
        self.client.login(username="playerstu", password="pw12345!")

    def test_player_content_endpoint_returns_partial_on_htmx(self):
        url = reverse("player_content", args=[self.course.id, self.content.id])
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shared/partials/_player_content.html")
        self.assertContains(response, "Hello world")
        self.assertNotContains(response, "<header")

    def test_player_content_requires_enrollment(self):
        other = User.objects.create_user(username="otherstu", password="pw12345!")
        self.client.login(username="otherstu", password="pw12345!")
        url = reverse("player_content", args=[self.course.id, self.content.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_mark_complete_post_creates_module_progress(self):
        from analytics.models import ModuleProgress
        url = reverse("mark_complete", args=[self.course.id, self.module.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        mp = ModuleProgress.objects.get(user=self.user, module=self.module)
        self.assertEqual(mp.status, "completed")

    def test_mark_complete_returns_progress_partial(self):
        url = reverse("mark_complete", args=[self.course.id, self.module.id])
        response = self.client.post(url)
        self.assertTemplateUsed(response, "shared/partials/_progress_panel.html")
        self.assertContains(response, "100%")

    def test_mark_complete_get_not_allowed(self):
        url = reverse("mark_complete", args=[self.course.id, self.module.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
