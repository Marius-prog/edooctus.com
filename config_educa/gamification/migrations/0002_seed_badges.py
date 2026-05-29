from django.db import migrations


DEFAULT_BADGES = [
    ("First Step", "first-step", "Enrolled in your first course.", "\U0001F331", 10, "first_course_enrolled"),
    ("Quiz Master", "quiz-passed", "Passed your first quiz.", "\U0001F9E0", 25, "quiz_passed"),
    ("Certified", "certified", "Earned a course certificate.", "\U0001F393", 100, "course_certified"),
    ("First Post", "first-post", "Wrote your first forum post.", "\U0001F4AC", 5, "forum_first_post"),
    ("Streak Starter", "streak-3", "3-day learning streak.", "\U0001F525", 15, "streak_3"),
    ("Streak Champion", "streak-30", "30-day learning streak.", "\U0001F3C6", 200, "streak_30"),
    ("Helpful Reviewer", "helpful-reviewer", "Wrote 5 helpful course reviews.", "\u2B50", 50, "five_helpful_reviews"),
    ("Mentor", "mentor", "Accepted as a mentor.", "\U0001F91D", 75, "became_mentor"),
]


def seed(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    for name, slug, desc, icon, pts, rule in DEFAULT_BADGES:
        Badge.objects.get_or_create(
            slug=slug,
            defaults=dict(name=name, description=desc, icon=icon,
                          points_reward=pts, rule_code=rule, is_active=True),
        )


def unseed(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    Badge.objects.filter(slug__in=[b[1] for b in DEFAULT_BADGES]).delete()


class Migration(migrations.Migration):
    dependencies = [("gamification", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
