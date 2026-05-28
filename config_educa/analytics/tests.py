from django.test import TestCase
from django.contrib.auth.models import User
from courses.models import Course, Module, Content
from .models import (
    CourseView, ModuleProgress, ContentInteraction,
    EnrollmentEvent, UserSession, LearningStreak
)


class AnalyticsModelsTestCase(TestCase):
    """Test cases for analytics models"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_models_import(self):
        """Test that all models can be imported"""
        self.assertIsNotNone(CourseView)
        self.assertIsNotNone(ModuleProgress)
        self.assertIsNotNone(ContentInteraction)
        self.assertIsNotNone(EnrollmentEvent)
        self.assertIsNotNone(UserSession)
        self.assertIsNotNone(LearningStreak)
