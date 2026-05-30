"""Cross-app integration tests: signals + celery tasks (eager mode)."""
from django.contrib.auth.models import User
from django.test import TestCase

from courses.models import Course, Subject
from gamification.models import UserBadge, user_points
from notifications.models import Notification


class EnrollmentSignalTests(TestCase):
    """Enrolling a student fires badge + notification."""

    @classmethod
    def setUpTestData(cls):
        cls.instr = User.objects.create_user("inst", password="pw12345!")
        cls.stu = User.objects.create_user("stu", password="pw12345!")
        cls.subj = Subject.objects.create(title="S", slug="s-sig")
        cls.course = Course.objects.create(
            owner=cls.instr, subject=cls.subj, title="C", slug="c-sig", overview="o"
        )

    def test_enrollment_awards_first_step_badge(self):
        self.assertEqual(UserBadge.objects.filter(user=self.stu).count(), 0)
        self.course.students.add(self.stu)
        self.assertEqual(
            UserBadge.objects.filter(user=self.stu, badge__slug="first-step").count(),
            1,
        )

    def test_enrollment_grants_points(self):
        self.course.students.add(self.stu)
        # First Step badge has points_reward=10 (from seed)
        self.assertEqual(user_points(self.stu), 10)

    def test_enrollment_creates_notifications(self):
        self.course.students.add(self.stu)
        # Should see at least: badge_earned + course_update
        kinds = set(Notification.objects.filter(user=self.stu).values_list("kind", flat=True))
        self.assertIn("badge_earned", kinds)
        self.assertIn("course_update", kinds)

    def test_double_enroll_is_idempotent(self):
        self.course.students.add(self.stu)
        self.course.students.add(self.stu)  # add again
        self.assertEqual(UserBadge.objects.filter(user=self.stu).count(), 1)


class QuizPassSignalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from quizzes.models import Quiz, Question, Choice
        cls.user = User.objects.create_user("qpu", password="pw12345!")
        cls.subj = Subject.objects.create(title="S", slug="s-qps")
        cls.course = Course.objects.create(
            owner=cls.user, subject=cls.subj, title="C", slug="c-qps", overview="o"
        )
        cls.quiz = Quiz.objects.create(course=cls.course, title="Q", pass_mark_pct=50)
        cls.q = Question.objects.create(quiz=cls.quiz, prompt="2+2?", points=1)
        cls.c_ok = Choice.objects.create(question=cls.q, text="4", is_correct=True)
        Choice.objects.create(question=cls.q, text="5", is_correct=False)

    def test_passing_quiz_awards_quiz_passed_badge_and_notifies(self):
        from quizzes.models import Submission, Answer
        sub = Submission.objects.create(quiz=self.quiz, user=self.user)
        a = Answer.objects.create(submission=sub, question=self.q)
        a.selected_choices.add(self.c_ok)
        sub.grade()
        # Badge
        self.assertTrue(
            UserBadge.objects.filter(user=self.user, badge__slug="quiz-passed").exists()
        )
        # Notification
        kinds = set(Notification.objects.filter(user=self.user).values_list("kind", flat=True))
        self.assertIn("quiz_graded", kinds)


class CelerySanityTests(TestCase):
    """Confirm Celery is configured + eager mode runs tasks inline."""

    def test_eager_mode_active(self):
        from django.conf import settings
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)

    def test_notifications_send_email_task_runs(self):
        from notifications.tasks import send_email_notification
        u = User.objects.create_user("etask", email="t@example.com", password="pw12345!")
        n = Notification.objects.create(user=u, kind="system", title="hi",
                                        body="hello", channel="email")
        result = send_email_notification.delay(n.id)
        # In eager mode, result.get() is immediate
        self.assertTrue(result.get(timeout=5))

    def test_privacy_export_task_generates_file(self):
        from privacy.models import DataExportRequest
        from privacy.tasks import generate_export
        u = User.objects.create_user("xu", password="pw12345!")
        req = DataExportRequest.objects.create(user=u)
        generate_export.delay(req.id).get(timeout=10)
        req.refresh_from_db()
        self.assertEqual(req.status, DataExportRequest.STATUS_READY)
        self.assertTrue(req.file)


class ProviderFactoryTests(TestCase):
    """Real provider factory falls back to FakeProvider when keys missing."""

    def test_get_provider_falls_back_to_fake_without_key(self):
        from ai_tools.models import AITool
        from ai_tools.providers import get_provider, FakeProvider
        from django.test import override_settings
        tool = AITool.objects.create(name="X", slug="x", provider="openai")
        with override_settings(OPENAI_API_KEY=""):
            p = get_provider(tool)
        self.assertIsInstance(p, FakeProvider)

    def test_fake_provider_returns_response_object(self):
        from ai_tools.providers import FakeProvider
        r = FakeProvider().call("hello world", model="echo")
        self.assertIn("hello world", r.text)
        self.assertGreater(r.tokens_input, 0)
        self.assertEqual(r.cost_micros, 0)  # echo is free
