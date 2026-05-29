from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from courses.models import Course, Subject
from .models import Quiz, Question, Choice, Submission, Answer, Rubric, RubricCriterion


class QuizEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("qu", password="pw12345!")
        cls.subject = Subject.objects.create(title="S", slug="s-qz")
        cls.course = Course.objects.create(
            owner=cls.user, subject=cls.subject, title="C", slug="c-qz", overview="o"
        )
        cls.quiz = Quiz.objects.create(course=cls.course, title="Q1", pass_mark_pct=50)
        cls.q1 = Question.objects.create(quiz=cls.quiz, prompt="2+2?", points=1, order=1)
        cls.c1 = Choice.objects.create(question=cls.q1, text="3", is_correct=False)
        cls.c2 = Choice.objects.create(question=cls.q1, text="4", is_correct=True)
        cls.q2 = Question.objects.create(quiz=cls.quiz, prompt="Sky?", points=1, order=2)
        cls.c3 = Choice.objects.create(question=cls.q2, text="Blue", is_correct=True)
        cls.c4 = Choice.objects.create(question=cls.q2, text="Green", is_correct=False)

    def test_quiz_total_points(self):
        self.assertEqual(self.quiz.total_points, 2)

    def test_perfect_submission_passes(self):
        sub = Submission.objects.create(quiz=self.quiz, user=self.user)
        a1 = Answer.objects.create(submission=sub, question=self.q1)
        a1.selected_choices.add(self.c2)
        a2 = Answer.objects.create(submission=sub, question=self.q2)
        a2.selected_choices.add(self.c3)
        pts, pct, passed = sub.grade()
        self.assertEqual(pts, 2)
        self.assertEqual(pct, 100.0)
        self.assertTrue(passed)
        self.assertEqual(sub.status, Submission.STATUS_GRADED)

    def test_half_correct_below_pass(self):
        self.quiz.pass_mark_pct = 75
        self.quiz.save()
        sub = Submission.objects.create(quiz=self.quiz, user=self.user)
        a1 = Answer.objects.create(submission=sub, question=self.q1)
        a1.selected_choices.add(self.c2)  # correct
        a2 = Answer.objects.create(submission=sub, question=self.q2)
        a2.selected_choices.add(self.c4)  # wrong
        pts, pct, passed = sub.grade()
        self.assertEqual(pts, 1)
        self.assertEqual(pct, 50.0)
        self.assertFalse(passed)

    def test_short_answer_uses_manual_score(self):
        sa = Question.objects.create(
            quiz=self.quiz, prompt="Explain.", question_type=Question.TYPE_SHORT,
            points=4, order=3,
        )
        sub = Submission.objects.create(quiz=self.quiz, user=self.user)
        ans = Answer.objects.create(
            submission=sub, question=sa, text_response="An essay.", awarded_points=3
        )
        # auto-pick the objective ones too
        Answer.objects.create(submission=sub, question=self.q1).selected_choices.add(self.c2)
        Answer.objects.create(submission=sub, question=self.q2).selected_choices.add(self.c3)
        pts, pct, passed = sub.grade()
        self.assertEqual(pts, 1 + 1 + 3)  # objective + manual

    def test_multi_choice_requires_exact_match(self):
        mq = Question.objects.create(
            quiz=self.quiz, prompt="Pick primes",
            question_type=Question.TYPE_MULTI, points=2, order=4,
        )
        a = Choice.objects.create(question=mq, text="2", is_correct=True)
        b = Choice.objects.create(question=mq, text="3", is_correct=True)
        Choice.objects.create(question=mq, text="4", is_correct=False)
        sub = Submission.objects.create(quiz=self.quiz, user=self.user)
        ans = Answer.objects.create(submission=sub, question=mq)
        ans.selected_choices.add(a)  # missing b
        sub.grade()
        ans.refresh_from_db()
        self.assertEqual(ans.awarded_points, 0)


class QuizAPISecurityTests(TestCase):
    """S3 (enrollment gate) + S4 (cross-quiz answer) + C4 (re-grade guard)."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("qowner", password="pw12345!")
        cls.student = User.objects.create_user("qstudent", password="pw12345!")
        cls.outsider = User.objects.create_user("qoutsider", password="pw12345!")
        cls.subject = Subject.objects.create(title="S", slug="s-qsec")
        cls.course = Course.objects.create(
            owner=cls.owner, subject=cls.subject, title="C", slug="c-qsec", overview="o"
        )
        cls.course.students.add(cls.student)
        cls.quiz = Quiz.objects.create(course=cls.course, title="Q", pass_mark_pct=50,
                                       is_published=True)
        cls.q = Question.objects.create(quiz=cls.quiz, prompt="2+2?", points=1, order=1)
        cls.correct = Choice.objects.create(question=cls.q, text="4", is_correct=True)
        # A second, unrelated quiz/question to test cross-quiz answer injection.
        cls.other_course = Course.objects.create(
            owner=cls.owner, subject=cls.subject, title="C2", slug="c2-qsec", overview="o"
        )
        cls.other_quiz = Quiz.objects.create(course=cls.other_course, title="Q2",
                                             is_published=True)
        cls.other_q = Question.objects.create(quiz=cls.other_quiz, prompt="x", points=1)

    def _api(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_enrolled_student_can_start(self):
        r = self._api(self.student).post(f"/quizzes/api/quizzes/{self.quiz.id}/start/")
        self.assertEqual(r.status_code, 201)

    def test_non_enrolled_user_cannot_start(self):
        r = self._api(self.outsider).post(f"/quizzes/api/quizzes/{self.quiz.id}/start/")
        self.assertEqual(r.status_code, 403)

    def test_owner_can_start(self):
        r = self._api(self.owner).post(f"/quizzes/api/quizzes/{self.quiz.id}/start/")
        self.assertEqual(r.status_code, 201)

    def test_non_enrolled_user_cannot_take_htmx(self):
        self.client.force_login(self.outsider)
        r = self.client.post(f"/quizzes/{self.quiz.id}/take/")
        self.assertEqual(r.status_code, 403)

    def test_answer_rejects_question_from_other_quiz(self):
        c = self._api(self.student)
        sub_id = c.post(f"/quizzes/api/quizzes/{self.quiz.id}/start/").data["id"]
        r = c.post(f"/quizzes/api/submissions/{sub_id}/answer/",
                   {"question": self.other_q.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cannot_resubmit_finalized_submission(self):
        c = self._api(self.student)
        sub_id = c.post(f"/quizzes/api/quizzes/{self.quiz.id}/start/").data["id"]
        self.assertEqual(c.post(f"/quizzes/api/submissions/{sub_id}/submit/").status_code, 200)
        # Second submit must be rejected (prevents re-grade / notification spam).
        self.assertEqual(c.post(f"/quizzes/api/submissions/{sub_id}/submit/").status_code, 400)


class RubricTests(TestCase):
    def test_rubric_with_criteria(self):
        r = Rubric.objects.create(name="Essay Rubric")
        RubricCriterion.objects.create(rubric=r, criterion="Clarity", max_points=5, order=1)
        RubricCriterion.objects.create(rubric=r, criterion="Depth", max_points=10, order=2)
        self.assertEqual(r.criteria.count(), 2)
        self.assertEqual(sum(c.max_points for c in r.criteria.all()), 15)
