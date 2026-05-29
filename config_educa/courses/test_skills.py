from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    Course, Subject, Skill, SkillDomain, CourseSkill, LearningOutcome,
)


class SkillTaxonomyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("sk", password="pw12345!")
        cls.subj = Subject.objects.create(title="S", slug="s-sk")
        cls.course = Course.objects.create(
            owner=cls.user, subject=cls.subj, title="Prompt 101",
            slug="prompt-101", overview="o",
        )
        cls.domain = SkillDomain.objects.create(name="Prompt Engineering",
                                                slug="prompt-engineering")
        cls.skill_a = Skill.objects.create(
            domain=cls.domain, name="Chain-of-thought prompting",
            slug="cot", bloom_level="apply",
        )
        cls.skill_b = Skill.objects.create(
            domain=cls.domain, name="System prompt design", slug="system-prompt",
        )

    def test_attach_skills_to_course(self):
        CourseSkill.objects.create(course=self.course, skill=self.skill_a,
                                   proficiency="intermediate", is_primary=True)
        CourseSkill.objects.create(course=self.course, skill=self.skill_b,
                                   proficiency="beginner")
        self.assertEqual(self.course.skills.count(), 2)
        primaries = self.course.course_skills.filter(is_primary=True)
        self.assertEqual(primaries.count(), 1)
        self.assertEqual(primaries.first().skill, self.skill_a)

    def test_skill_unique_per_course(self):
        CourseSkill.objects.create(course=self.course, skill=self.skill_a)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            CourseSkill.objects.create(course=self.course, skill=self.skill_a)

    def test_reverse_lookup(self):
        CourseSkill.objects.create(course=self.course, skill=self.skill_a)
        self.assertIn(self.course, self.skill_a.courses.all())

    def test_learning_outcomes(self):
        LearningOutcome.objects.create(
            course=self.course, statement="Design a multi-step prompt.",
            skill=self.skill_a, order=1,
        )
        LearningOutcome.objects.create(
            course=self.course, statement="Critique an LLM response.", order=2,
        )
        outcomes = list(self.course.learning_outcomes.all())
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes[0].order, 1)
        # Outcome can reference a skill or be free-standing
        self.assertIsNotNone(outcomes[0].skill)
        self.assertIsNone(outcomes[1].skill)

    def test_skill_unique_slug(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Skill.objects.create(domain=self.domain, name="dup", slug="cot")
