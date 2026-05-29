from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import MentorProfile, MentorshipRequest, MentorshipSession, find_mentors


class MentorshipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("malice", password="pw12345!")
        cls.bob = User.objects.create_user("mbob", password="pw12345!")
        cls.cara = User.objects.create_user("mcara", password="pw12345!")
        cls.bob_profile = MentorProfile.objects.create(
            user=cls.bob, expertise=["python", "django"], avg_rating=4.5,
        )
        cls.cara_profile = MentorProfile.objects.create(
            user=cls.cara, expertise=["openai", "prompting"], avg_rating=4.0,
        )

    def test_request_and_accept(self):
        r = MentorshipRequest.objects.create(mentee=self.alice, mentor=self.bob)
        self.assertEqual(r.status, MentorshipRequest.STATUS_PENDING)
        r.accept()
        self.assertEqual(r.status, MentorshipRequest.STATUS_ACCEPTED)
        self.assertIsNotNone(r.responded_at)

    def test_cannot_mentor_self(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            MentorshipRequest.objects.create(mentee=self.alice, mentor=self.alice)

    def test_has_capacity_respects_limit(self):
        self.bob_profile.max_active_mentees = 1
        self.bob_profile.save()
        MentorshipRequest.objects.create(
            mentee=self.alice, mentor=self.bob,
            status=MentorshipRequest.STATUS_ACCEPTED,
        )
        self.assertFalse(self.bob_profile.has_capacity())

    def test_find_mentors_by_expertise(self):
        matches = find_mentors(["openai"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], self.cara_profile)

    def test_find_mentors_no_tags_returns_by_rating(self):
        matches = find_mentors([])
        self.assertEqual(matches[0], self.bob_profile)  # higher avg_rating

    def test_decline_and_end(self):
        r = MentorshipRequest.objects.create(mentee=self.alice, mentor=self.bob)
        r.decline()
        self.assertEqual(r.status, MentorshipRequest.STATUS_DECLINED)
        r2 = MentorshipRequest.objects.create(
            mentee=self.alice, mentor=self.cara,
            status=MentorshipRequest.STATUS_ACCEPTED,
        )
        r2.end()
        self.assertEqual(r2.status, MentorshipRequest.STATUS_ENDED)


class MentorshipAPISecurityTests(TestCase):
    """S1: profile/session writes must be restricted to the owning user."""

    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user("smbob", password="pw12345!")
        cls.alice = User.objects.create_user("smalice", password="pw12345!")
        cls.attacker = User.objects.create_user("smattacker", password="pw12345!")
        cls.bob_profile = MentorProfile.objects.create(user=cls.bob, expertise=["python"])
        cls.pairing = MentorshipRequest.objects.create(
            mentee=cls.alice, mentor=cls.bob,
            status=MentorshipRequest.STATUS_ACCEPTED,
        )

    def _api(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_attacker_cannot_edit_others_profile(self):
        r = self._api(self.attacker).patch(f"/mentorship/api/mentors/{self.bob_profile.id}/",
                                           {"bio": "hijacked"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_attacker_cannot_delete_others_profile(self):
        r = self._api(self.attacker).delete(f"/mentorship/api/mentors/{self.bob_profile.id}/")
        self.assertEqual(r.status_code, 403)

    def test_owner_can_edit_own_profile(self):
        r = self._api(self.bob).patch(f"/mentorship/api/mentors/{self.bob_profile.id}/",
                                      {"bio": "updated"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_can_read_other_profiles(self):
        # Discovery must still work — reads are open to authenticated users.
        r = self._api(self.attacker).get(f"/mentorship/api/mentors/{self.bob_profile.id}/")
        self.assertEqual(r.status_code, 200)

    def test_attacker_cannot_create_session_for_others_pairing(self):
        r = self._api(self.attacker).post(
            "/mentorship/api/sessions/",
            {"pairing": self.pairing.id, "scheduled_at": "2030-01-01T10:00:00Z",
             "duration_minutes": 30}, format="json")
        self.assertIn(r.status_code, (403, 400))
        self.assertEqual(MentorshipSession.objects.count(), 0)

    def test_participant_can_create_session_for_own_pairing(self):
        r = self._api(self.bob).post(
            "/mentorship/api/sessions/",
            {"pairing": self.pairing.id, "scheduled_at": "2030-01-01T10:00:00Z",
             "duration_minutes": 30}, format="json")
        self.assertEqual(r.status_code, 201)
