"""HTMX endpoint + DRF API smoke tests for the quizzes app."""
import sys
import unittest

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from courses.models import Course, Subject
from .models import Quiz, Question, Choice, Submission


# Django 4.2's template-context copy is incompatible with Python 3.14.
# Tests that render templates via the test client are skipped on 3.14 only;
# they run normally on production Python 3.10.
_PY314_TEMPLATE_BUG = sys.version_info >= (3, 14)
skip_if_py314_templates = unittest.skipIf(
    _PY314_TEMPLATE_BUG, "Django 4.2 template-context copy broken on Python 3.14",
)


class QuizHtmxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("qhx", password="pw12345!")
        cls.subj = Subject.objects.create(title="S", slug="s-qhx")
        cls.course = Course.objects.create(
            owner=cls.user, subject=cls.subj, title="C",
            slug="c-qhx", overview="o",
        )
        cls.quiz = Quiz.objects.create(course=cls.course, title="Q",
                                       pass_mark_pct=50, is_published=True,
                                       max_attempts=2)
        cls.q = Question.objects.create(quiz=cls.quiz, prompt="2+2?", points=1)
        cls.c_ok = Choice.objects.create(question=cls.q, text="4", is_correct=True)
        cls.c_bad = Choice.objects.create(question=cls.q, text="5", is_correct=False)

    def setUp(self):
        self.client = Client()
        self.client.login(username="qhx", password="pw12345!")

    @skip_if_py314_templates
    def test_take_endpoint_grades_and_creates_submission(self):
        url = reverse("quizzes:take", args=[self.quiz.id])
        resp = self.client.post(url, {f"q_{self.q.id}": [self.c_ok.id]})
        self.assertEqual(resp.status_code, 200)
        # Avoid assertContains (template-context copy hits a Py3.14 bug in dev);
        # check the rendered bytes directly.
        self.assertIn(b"Passed", resp.content)
        subs = Submission.objects.filter(user=self.user)
        self.assertEqual(subs.count(), 1)
        self.assertTrue(subs.first().passed)

    @skip_if_py314_templates
    def test_take_rejects_after_max_attempts(self):
        url = reverse("quizzes:take", args=[self.quiz.id])
        for _ in range(2):
            self.client.post(url, {f"q_{self.q.id}": [self.c_ok.id]})
        resp = self.client.post(url, {f"q_{self.q.id}": [self.c_ok.id]})
        self.assertEqual(resp.status_code, 403)


class QuizAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("qapi", password="pw12345!")
        cls.subj = Subject.objects.create(title="S", slug="s-qapi")
        cls.course = Course.objects.create(
            owner=cls.user, subject=cls.subj, title="C", slug="c-qapi", overview="o"
        )
        cls.quiz = Quiz.objects.create(course=cls.course, title="Q",
                                       is_published=True, pass_mark_pct=50)
        cls.q = Question.objects.create(quiz=cls.quiz, prompt="?", points=1)
        cls.c = Choice.objects.create(question=cls.q, text="x", is_correct=True)

    def setUp(self):
        self.client.login(username="qapi", password="pw12345!")

    def test_quiz_list_returns_published_only(self):
        resp = self.client.get("/quizzes/api/quizzes/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_start_creates_submission(self):
        resp = self.client.post(f"/quizzes/api/quizzes/{self.quiz.id}/start/")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Submission.objects.count(), 1)

    def test_answer_and_submit_flow(self):
        # Start
        r = self.client.post(f"/quizzes/api/quizzes/{self.quiz.id}/start/")
        sub_id = r.json()["id"]
        # Answer
        r = self.client.post(
            f"/quizzes/api/submissions/{sub_id}/answer/",
            data={"question": self.q.id, "selected_choice_ids": [self.c.id]},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        # Submit
        r = self.client.post(f"/quizzes/api/submissions/{sub_id}/submit/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "graded")
        self.assertTrue(r.json()["passed"])
