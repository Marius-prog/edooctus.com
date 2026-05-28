from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from courses.models import Course, Subject, Module
from students.forms import CourseEnrollForm


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
