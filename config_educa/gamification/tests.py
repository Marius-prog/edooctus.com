from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    Badge, UserBadge, PointsTransaction,
    award_badge, user_points, leaderboard,
)


class GamificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", password="pw12345!")
        cls.bob = User.objects.create_user("bob", password="pw12345!")
        # Seed migration already creates "first-step"; idempotent get-or-create.
        cls.badge, _ = Badge.objects.update_or_create(
            slug="first-step",
            defaults=dict(name="First Step", rule_code="first_course_enrolled",
                          points_reward=10, is_active=True),
        )

    def test_award_badge_creates_userbadge_and_points(self):
        ub = award_badge(self.alice, "first-step", awarded_for="enrolled in Calculus")
        self.assertIsNotNone(ub)
        self.assertEqual(user_points(self.alice), 10)

    def test_award_badge_is_idempotent(self):
        award_badge(self.alice, "first-step")
        award_badge(self.alice, "first-step")
        self.assertEqual(UserBadge.objects.filter(user=self.alice).count(), 1)
        self.assertEqual(user_points(self.alice), 10)  # only one payout

    def test_award_unknown_badge_returns_none(self):
        self.assertIsNone(award_badge(self.alice, "does-not-exist"))

    def test_points_transactions_sum_correctly(self):
        PointsTransaction.objects.create(user=self.alice, delta=50, reason="quiz")
        PointsTransaction.objects.create(user=self.alice, delta=-20, reason="spent")
        self.assertEqual(user_points(self.alice), 30)

    def test_leaderboard_orders_by_total_desc(self):
        PointsTransaction.objects.create(user=self.alice, delta=100, reason="x")
        PointsTransaction.objects.create(user=self.bob, delta=200, reason="x")
        lb = list(leaderboard(limit=5))
        self.assertEqual(lb[0]["user__username"], "bob")
        self.assertEqual(lb[0]["total"], 200)

    def test_inactive_badge_not_awarded(self):
        self.badge.is_active = False
        self.badge.save()
        self.assertIsNone(award_badge(self.alice, "first-step"))
