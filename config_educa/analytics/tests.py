from datetime import date, timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from courses.models import Course, Module, Content, Subject, Text
from .models import (
    CourseView, ModuleProgress, ContentInteraction,
    EnrollmentEvent, UserSession, LearningStreak,
)


class AnalyticsTestBase(TestCase):
    """Shared fixtures."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="ana_user", password="pw12345!")
        cls.instructor = User.objects.create_user(username="ana_instr", password="pw12345!")
        cls.subject = Subject.objects.create(title="AnaSubj", slug="ana-subj")
        cls.course = Course.objects.create(
            owner=cls.instructor, subject=cls.subject,
            title="AnaCourse", slug="ana-course", overview="ov",
        )
        cls.module = Module.objects.create(course=cls.course, title="M1", description="d")
        text_item = Text.objects.create(owner=cls.instructor, title="T1", content="hi")
        cls.content = Content.objects.create(
            module=cls.module,
            content_type=ContentType.objects.get_for_model(Text),
            object_id=text_item.id,
        )


class CourseViewTests(AnalyticsTestBase):
    def test_create_course_view(self):
        cv = CourseView.objects.create(
            course=self.course, user=self.user,
            session_id="s" * 40, ip_address="127.0.0.1",
        )
        self.assertIsNotNone(cv.viewed_at)
        self.assertIn(self.course.title, str(cv))

    def test_view_persists_when_user_deleted(self):
        cv = CourseView.objects.create(course=self.course, user=self.user, session_id="x")
        self.user.delete()
        cv.refresh_from_db()
        self.assertIsNone(cv.user)  # SET_NULL

    def test_indexes_declared(self):
        index_fields = {tuple(i.fields) for i in CourseView._meta.indexes}
        self.assertIn(("course", "-viewed_at"), index_fields)
        self.assertIn(("user", "-viewed_at"), index_fields)
        self.assertIn(("session_id", "-viewed_at"), index_fields)


class ModuleProgressTests(AnalyticsTestBase):
    def test_unique_per_user_module(self):
        ModuleProgress.objects.create(user=self.user, module=self.module)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            ModuleProgress.objects.create(user=self.user, module=self.module)

    def test_mark_started_sets_timestamp_and_status(self):
        mp = ModuleProgress.objects.create(user=self.user, module=self.module)
        self.assertIsNone(mp.started_at)
        mp.mark_started()
        mp.refresh_from_db()
        self.assertEqual(mp.status, "in_progress")
        self.assertIsNotNone(mp.started_at)

    def test_mark_started_is_idempotent(self):
        mp = ModuleProgress.objects.create(user=self.user, module=self.module)
        mp.mark_started()
        first = mp.started_at
        mp.mark_started()
        mp.refresh_from_db()
        self.assertEqual(mp.started_at, first)

    def test_mark_completed_sets_status_and_timestamp(self):
        mp = ModuleProgress.objects.create(user=self.user, module=self.module)
        mp.mark_completed()
        mp.refresh_from_db()
        self.assertEqual(mp.status, "completed")
        self.assertIsNotNone(mp.completed_at)

    def test_completion_time_hours_none_when_incomplete(self):
        mp = ModuleProgress.objects.create(user=self.user, module=self.module)
        self.assertIsNone(mp.completion_time_hours)

    def test_completion_time_hours_computed(self):
        now = timezone.now()
        mp = ModuleProgress.objects.create(
            user=self.user, module=self.module,
            started_at=now - timedelta(hours=2), completed_at=now,
            status="completed",
        )
        self.assertAlmostEqual(mp.completion_time_hours, 2.0, places=1)


class ContentInteractionTests(AnalyticsTestBase):
    def test_create_interaction(self):
        ci = ContentInteraction.objects.create(
            user=self.user, content=self.content,
            interaction_type="view",
        )
        self.assertEqual(ci.interaction_type, "view")
        self.assertFalse(ci.completed)
        self.assertIsNotNone(ci.timestamp)

    def test_ordering_desc_by_timestamp(self):
        a = ContentInteraction.objects.create(user=self.user, content=self.content, interaction_type="view")
        b = ContentInteraction.objects.create(user=self.user, content=self.content, interaction_type="play")
        self.assertEqual(list(ContentInteraction.objects.all())[:2], [b, a])


class EnrollmentEventTests(AnalyticsTestBase):
    def test_event_with_metadata(self):
        ev = EnrollmentEvent.objects.create(
            user=self.user, course=self.course,
            event_type="enrolled", metadata={"source": "landing"},
        )
        ev.refresh_from_db()
        self.assertEqual(ev.metadata["source"], "landing")

    def test_funnel_ordering(self):
        for et in ["course_view", "enroll_click", "enrolled"]:
            EnrollmentEvent.objects.create(user=self.user, course=self.course, event_type=et)
        events = list(EnrollmentEvent.objects.filter(user=self.user).order_by("timestamp"))
        self.assertEqual([e.event_type for e in events],
                         ["course_view", "enroll_click", "enrolled"])


class UserSessionTests(AnalyticsTestBase):
    def test_session_key_unique(self):
        UserSession.objects.create(user=self.user, session_key="abc")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            UserSession.objects.create(user=self.user, session_key="abc")

    def test_duration_minutes_falls_back_to_last_activity(self):
        s = UserSession.objects.create(user=self.user, session_key="dur1")
        # No ended_at — duration uses last_activity (auto_now), which is ~now
        self.assertGreaterEqual(s.duration_minutes, 0.0)
        self.assertLess(s.duration_minutes, 1.0)

    def test_duration_minutes_with_ended_at(self):
        s = UserSession.objects.create(user=self.user, session_key="dur2")
        s.ended_at = s.started_at + timedelta(minutes=30)
        s.save()
        self.assertAlmostEqual(s.duration_minutes, 30.0, places=1)


class LearningStreakTests(AnalyticsTestBase):
    def test_unique_per_user_date(self):
        LearningStreak.objects.create(user=self.user, date=date.today())
        with transaction.atomic(), self.assertRaises(IntegrityError):
            LearningStreak.objects.create(user=self.user, date=date.today())

    def test_get_current_streak_zero_when_no_records(self):
        self.assertEqual(LearningStreak.get_current_streak(self.user), 0)

    def test_get_current_streak_counts_consecutive_days(self):
        today = date.today()
        for offset in range(3):  # today, yesterday, day-before
            LearningStreak.objects.create(user=self.user, date=today - timedelta(days=offset))
        self.assertEqual(LearningStreak.get_current_streak(self.user), 3)

    def test_get_current_streak_breaks_on_gap(self):
        today = date.today()
        LearningStreak.objects.create(user=self.user, date=today)
        # skip yesterday
        LearningStreak.objects.create(user=self.user, date=today - timedelta(days=2))
        self.assertEqual(LearningStreak.get_current_streak(self.user), 1)

    def test_courses_accessed_m2m(self):
        s = LearningStreak.objects.create(user=self.user, date=date.today())
        s.courses_accessed.add(self.course)
        self.assertIn(self.course, s.courses_accessed.all())
