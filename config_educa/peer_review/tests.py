from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course, Subject
from .models import Assignment, Submission, PeerReview


class PeerReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user("pra", password="pw12345!")
        cls.r1 = User.objects.create_user("prr1", password="pw12345!")
        cls.r2 = User.objects.create_user("prr2", password="pw12345!")
        cls.subj = Subject.objects.create(title="S", slug="s-pr")
        cls.course = Course.objects.create(
            owner=cls.author, subject=cls.subj, title="C", slug="c-pr", overview="o"
        )
        cls.assign = Assignment.objects.create(
            course=cls.course, title="A1", instructions="Do it.",
            peer_reviews_required=2,
        )

    def test_submission_lifecycle(self):
        s = Submission.objects.create(assignment=self.assign, author=self.author, content="x")
        self.assertEqual(s.status, Submission.STATUS_DRAFT)
        s.submit()
        self.assertEqual(s.status, Submission.STATUS_SUBMITTED)
        self.assertIsNotNone(s.submitted_at)

    def test_peer_review_updates_avg_and_status(self):
        s = Submission.objects.create(assignment=self.assign, author=self.author, content="x")
        s.submit()
        PeerReview.objects.create(submission=s, reviewer=self.r1, score=Decimal("80"))
        s.refresh_from_db()
        self.assertEqual(s.review_count, 1)
        self.assertEqual(s.status, Submission.STATUS_SUBMITTED)  # not enough reviews yet
        PeerReview.objects.create(submission=s, reviewer=self.r2, score=Decimal("90"))
        s.refresh_from_db()
        self.assertEqual(s.review_count, 2)
        self.assertEqual(s.avg_score, Decimal("85.00"))
        self.assertEqual(s.status, Submission.STATUS_REVIEWED)

    def test_cannot_review_own_submission(self):
        s = Submission.objects.create(assignment=self.assign, author=self.author, content="x")
        review = PeerReview(submission=s, reviewer=self.author, score=Decimal("100"))
        with self.assertRaises(ValidationError):
            review.clean()

    def test_score_must_be_in_range(self):
        from django.db.utils import IntegrityError
        s = Submission.objects.create(assignment=self.assign, author=self.author, content="x")
        with self.assertRaises(IntegrityError):
            PeerReview.objects.create(submission=s, reviewer=self.r1, score=Decimal("150"))

    def test_unique_review_per_reviewer(self):
        from django.db.utils import IntegrityError
        from django.db import transaction
        s = Submission.objects.create(assignment=self.assign, author=self.author, content="x")
        PeerReview.objects.create(submission=s, reviewer=self.r1, score=Decimal("50"))
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PeerReview.objects.create(submission=s, reviewer=self.r1, score=Decimal("60"))
