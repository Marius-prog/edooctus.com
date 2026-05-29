from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from courses.models import Course, Subject
from .models import ForumCategory, Topic, Post, PostVote


class ForumTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("fu", password="pw12345!")
        cls.user2 = User.objects.create_user("fu2", password="pw12345!")
        cls.subject = Subject.objects.create(title="S", slug="s-fo")
        cls.course = Course.objects.create(
            owner=cls.user, subject=cls.subject, title="C", slug="c-fo", overview="o"
        )
        cls.cat = ForumCategory.objects.create(course=cls.course, name="General", slug="general")
        cls.topic = Topic.objects.create(
            category=cls.cat, author=cls.user, title="Hello", slug="hello"
        )

    def test_post_creation_updates_topic_last_activity(self):
        old = self.topic.last_activity
        Post.objects.create(topic=self.topic, author=self.user2, body="reply")
        self.topic.refresh_from_db()
        self.assertGreaterEqual(self.topic.last_activity, old)

    def test_threaded_replies(self):
        p1 = Post.objects.create(topic=self.topic, author=self.user, body="root")
        Post.objects.create(topic=self.topic, parent=p1, author=self.user2, body="nested")
        self.assertEqual(p1.replies.count(), 1)

    def test_postvote_uniqueness(self):
        p = Post.objects.create(topic=self.topic, author=self.user, body="x")
        PostVote.objects.create(post=p, user=self.user2)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PostVote.objects.create(post=p, user=self.user2)

    def test_pinned_topic_orders_first(self):
        Topic.objects.create(
            category=self.cat, author=self.user, title="newer", slug="newer",
            last_activity=timezone.now(),
        )
        self.topic.is_pinned = True
        self.topic.save()
        first = Topic.objects.first()
        self.assertEqual(first, self.topic)

    def test_moderation_flags(self):
        p = Post.objects.create(topic=self.topic, author=self.user2, body="bad")
        p.is_flagged = True
        p.flag_reason = "spam"
        p.is_hidden = True
        p.save()
        self.assertEqual(Post.objects.filter(is_flagged=True).count(), 1)
        self.assertEqual(Post.objects.filter(is_hidden=False).count(), 0)


class ForumAPISecurityTests(TestCase):
    """S2: only the author may edit/delete a topic/post (IDOR)."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user("fauthor", password="pw12345!")
        cls.attacker = User.objects.create_user("fattacker", password="pw12345!")
        cls.subject = Subject.objects.create(title="S", slug="s-fsec")
        cls.course = Course.objects.create(
            owner=cls.author, subject=cls.subject, title="C", slug="c-fsec", overview="o"
        )
        cls.cat = ForumCategory.objects.create(course=cls.course, name="Gen", slug="gen-sec")
        cls.topic = Topic.objects.create(category=cls.cat, author=cls.author,
                                         title="T", slug="t-sec")
        cls.post = Post.objects.create(topic=cls.topic, author=cls.author, body="mine")

    def _api(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_attacker_cannot_edit_others_topic(self):
        r = self._api(self.attacker).patch(f"/forum/api/topics/{self.topic.id}/",
                                           {"title": "hijacked"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_attacker_cannot_delete_others_post(self):
        r = self._api(self.attacker).delete(f"/forum/api/posts/{self.post.id}/")
        self.assertEqual(r.status_code, 403)

    def test_author_can_edit_own_post(self):
        r = self._api(self.author).patch(f"/forum/api/posts/{self.post.id}/",
                                         {"body": "edited"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_anyone_can_upvote_others_post(self):
        # Upvoting/flagging others' content must still work (not an ownership write).
        r = self._api(self.attacker).post(f"/forum/api/posts/{self.post.id}/upvote/")
        self.assertEqual(r.status_code, 200)
