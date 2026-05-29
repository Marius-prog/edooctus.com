"""Cross-app reactions: award badges + send notifications on key events.

Signals fire in-process. Heavy work goes via Celery tasks (`.tasks`).
"""
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from courses.models import Course
from .models import award_badge


# 1. First-enrollment badge --------------------------------------------------
@receiver(m2m_changed, sender=Course.students.through)
def on_course_students_changed(sender, instance, action, pk_set, **kwargs):
    """When a student enrolls in their first course \u2192 award 'first-step'."""
    if action != "post_add" or not pk_set:
        return
    from django.contrib.auth import get_user_model
    User = get_user_model()
    from notifications.models import notify
    for user_id in pk_set:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            continue
        ub = award_badge(user, "first-step", awarded_for=f"Enrolled in {instance.title}")
        if ub:
            notify(
                user, "badge_earned",
                title=f"You earned a badge: {ub.badge.name}",
                body=ub.badge.description,
                link="/students/badges/",
                metadata={"badge_slug": ub.badge.slug},
            )
        # Always notify on enrollment
        notify(
            user, "course_update",
            title=f"Welcome to {instance.title}!",
            body="You're enrolled. Start your first module any time.",
            link=f"/students/courses/{instance.id}/",
        )


# 2. Quiz pass \u2192 award + notify
try:
    from quizzes.models import Submission as QuizSubmission

    @receiver(post_save, sender=QuizSubmission)
    def on_quiz_submission_saved(sender, instance, created, **kwargs):
        if instance.status != QuizSubmission.STATUS_GRADED:
            return
        from notifications.models import notify
        if instance.passed:
            award_badge(instance.user, "quiz-passed",
                        awarded_for=f"Passed {instance.quiz.title}")
            notify(
                instance.user, "quiz_graded",
                title=f"\u2705 You passed {instance.quiz.title}",
                body=f"Score: {instance.score_pct}%",
                link=f"/quizzes/{instance.quiz_id}/",
            )
        else:
            notify(
                instance.user, "quiz_graded",
                title=f"Quiz result: {instance.quiz.title}",
                body=f"Score: {instance.score_pct}% (pass mark {instance.quiz.pass_mark_pct}%). Try again!",
                link=f"/quizzes/{instance.quiz_id}/",
            )
except Exception:  # pragma: no cover  \u2014 app may not be installed
    pass


# 3. Certificate earned
try:
    from certificates.models import Certificate

    @receiver(post_save, sender=Certificate)
    def on_certificate_created(sender, instance, created, **kwargs):
        if not created:
            return
        from notifications.models import notify
        award_badge(instance.user, "certified",
                    awarded_for=f"Certificate for {instance.course.title}")
        notify(
            instance.user, "certificate_ready",
            title="\U0001F393 Your certificate is ready!",
            body=f"For course: {instance.course.title}",
            link="/certificates/my/",
        )
except Exception:  # pragma: no cover
    pass


# 4. Forum reply \u2192 notify topic author + first-post badge
try:
    from forum.models import Post

    @receiver(post_save, sender=Post)
    def on_forum_post_created(sender, instance, created, **kwargs):
        if not created:
            return
        from notifications.models import notify
        award_badge(instance.author, "first-post",
                    awarded_for="First forum post")
        topic = instance.topic
        if topic.author_id != instance.author_id:
            notify(
                topic.author, "forum_reply",
                title=f"New reply on '{topic.title}'",
                body=instance.body[:200],
                link=f"/forum/topic/{topic.id}/",
                metadata={"post_id": instance.id},
            )
except Exception:  # pragma: no cover
    pass
