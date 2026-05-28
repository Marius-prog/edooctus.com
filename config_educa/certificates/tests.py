from django.test import TestCase
from django.contrib.auth.models import User
from courses.models import Course, Subject, Module
from analytics.models import ModuleProgress
from .models import Certificate, CertificateTemplate
from .utils import check_course_completion


class CertificateModelTest(TestCase):
    """Test Certificate model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.instructor = User.objects.create_user(username='instructor', password='testpass123')
        self.subject = Subject.objects.create(title='Test Subject', slug='test-subject')
        self.course = Course.objects.create(
            owner=self.instructor,
            subject=self.subject,
            title='Test Course',
            slug='test-course',
            overview='Test overview'
        )

    def test_certificate_creation(self):
        """Test creating a certificate"""
        certificate = Certificate.objects.create(
            user=self.user,
            course=self.course
        )
        self.assertIsNotNone(certificate.certificate_id)
        self.assertIsNotNone(certificate.verification_code)
        self.assertTrue(certificate.is_valid)
        self.assertEqual(certificate.download_count, 0)

    def test_verification_code_unique(self):
        """Test that verification codes are unique"""
        cert1 = Certificate.objects.create(user=self.user, course=self.course)
        user2 = User.objects.create_user(username='user2', password='testpass123')
        cert2 = Certificate.objects.create(user=user2, course=self.course)
        self.assertNotEqual(cert1.verification_code, cert2.verification_code)

    def test_certificate_revoke(self):
        """Test revoking a certificate"""
        certificate = Certificate.objects.create(user=self.user, course=self.course)
        self.assertTrue(certificate.is_valid)
        certificate.revoke('Test revocation')
        self.assertFalse(certificate.is_valid)
        self.assertIsNotNone(certificate.revoked_at)
        self.assertEqual(certificate.revoked_reason, 'Test revocation')

    def test_track_download(self):
        """Test tracking certificate downloads"""
        certificate = Certificate.objects.create(user=self.user, course=self.course)
        self.assertEqual(certificate.download_count, 0)
        certificate.track_download()
        self.assertEqual(certificate.download_count, 1)
        self.assertIsNotNone(certificate.last_downloaded)


class CourseCompletionTest(TestCase):
    """Test course completion checking"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.instructor = User.objects.create_user(username='instructor', password='testpass123')
        self.subject = Subject.objects.create(title='Test Subject', slug='test-subject')
        self.course = Course.objects.create(
            owner=self.instructor,
            subject=self.subject,
            title='Test Course',
            slug='test-course',
            overview='Test overview'
        )
        self.module1 = Module.objects.create(
            course=self.course,
            title='Module 1',
            description='Test module 1'
        )
        self.module2 = Module.objects.create(
            course=self.course,
            title='Module 2',
            description='Test module 2'
        )

    def test_course_not_completed(self):
        """Test course with no completed modules"""
        completed = check_course_completion(self.user, self.course)
        self.assertFalse(completed)

    def test_course_partially_completed(self):
        """Test course with some modules completed"""
        ModuleProgress.objects.create(
            user=self.user,
            module=self.module1,
            status='completed'
        )
        completed = check_course_completion(self.user, self.course)
        self.assertFalse(completed)

    def test_course_fully_completed(self):
        """Test course with all modules completed"""
        ModuleProgress.objects.create(
            user=self.user,
            module=self.module1,
            status='completed'
        )
        ModuleProgress.objects.create(
            user=self.user,
            module=self.module2,
            status='completed'
        )
        completed = check_course_completion(self.user, self.course)
        self.assertTrue(completed)


class CertificateTemplateTest(TestCase):
    """Test CertificateTemplate model"""

    def test_default_template_single(self):
        """Test that only one default template can exist"""
        template1 = CertificateTemplate.objects.create(
            name='Template 1',
            html_template='<html>Test 1</html>',
            css_styles='body { color: red; }',
            is_default=True
        )
        self.assertTrue(template1.is_default)

        template2 = CertificateTemplate.objects.create(
            name='Template 2',
            html_template='<html>Test 2</html>',
            css_styles='body { color: blue; }',
            is_default=True
        )
        self.assertTrue(template2.is_default)

        # Refresh template1 from database
        template1.refresh_from_db()
        self.assertFalse(template1.is_default)
