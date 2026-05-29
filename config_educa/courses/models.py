from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .fields import OrderField
from django.template.loader import render_to_string


class Subject(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Competency / skill taxonomy
#   Skill  --belongs-to-->  SkillDomain
#   Course --M2M-->  Skill (with proficiency level via through-model)
#   LearningOutcome  --belongs-to-->  Course  ("By the end of this course, learner can ...")
# ---------------------------------------------------------------------------

PROFICIENCY_CHOICES = [
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'),
    ('advanced', 'Advanced'),
    ('expert', 'Expert'),
]


class SkillDomain(models.Model):
    """Top-level grouping, e.g. 'Prompt Engineering', 'Image Generation'."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Skill(models.Model):
    """An atomic competency a learner can acquire."""
    domain = models.ForeignKey(
        SkillDomain, on_delete=models.CASCADE, related_name='skills'
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    bloom_level = models.CharField(
        max_length=20, blank=True,
        help_text="Bloom's taxonomy verb (remember/understand/apply/analyze/evaluate/create).",
    )

    class Meta:
        ordering = ['domain', 'name']
        indexes = [models.Index(fields=['domain', 'name'])]

    def __str__(self):
        return f"{self.domain.name} · {self.name}"


class CourseSkill(models.Model):
    """Through-model: which skills a course teaches and at what proficiency."""
    course = models.ForeignKey(
        'Course', on_delete=models.CASCADE, related_name='course_skills'
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.CASCADE, related_name='taught_in_courses'
    )
    proficiency = models.CharField(
        max_length=20, choices=PROFICIENCY_CHOICES, default='intermediate'
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ['course', 'skill']
        ordering = ['-is_primary', 'skill']

    def __str__(self):
        return f"{self.course} → {self.skill} ({self.proficiency})"


class LearningOutcome(models.Model):
    """Outcome statement ("learner will be able to ...") attached to a course."""
    course = models.ForeignKey(
        'Course', on_delete=models.CASCADE, related_name='learning_outcomes'
    )
    statement = models.TextField(
        help_text='Action-verb-led outcome, e.g. "Design a multi-step prompt chain."'
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='outcomes',
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        indexes = [models.Index(fields=['course', 'order'])]

    def __str__(self):
        return self.statement[:80]


class Course(models.Model):
    owner = models.ForeignKey(User,
                              related_name='courses_created',
                              on_delete=models.CASCADE)

    subject = models.ForeignKey(Subject,
                                related_name='courses',
                                on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    overview = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    students = models.ManyToManyField(User,
                                      related_name='courses_joined',
                                      blank=True)
    skills = models.ManyToManyField(
        Skill, through='CourseSkill', related_name='courses',
        blank=True,
    )
    # Rating fields
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average rating from reviews"
    )
    total_reviews = models.IntegerField(default=0, help_text="Total number of reviews")

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created']),
            models.Index(fields=['owner', '-created']),
            models.Index(fields=['subject', '-created']),
        ]

    def __str__(self):
        return self.title

    def update_rating(self):
        """Calculate and update average rating"""
        from reviews.models import CourseReview
        reviews = CourseReview.objects.filter(course=self)
        if reviews.exists():
            from django.db.models import Avg, Count
            stats = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
            self.average_rating = stats['avg'] or 0
            self.total_reviews = stats['count'] or 0
        else:
            self.average_rating = 0
            self.total_reviews = 0
        self.save(update_fields=['average_rating', 'total_reviews'])


class Module(models.Model):
    course = models.ForeignKey(Course,
                               related_name='modules',
                               on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = OrderField(blank=True, for_fields=['course'])

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.order}. {self.title}'


class Content(models.Model):
    module = models.ForeignKey(Module,
                               related_name='contents',
                               on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType,
                                     on_delete=models.CASCADE,
                                     limit_choices_to={'model__in': (
                                         'text',
                                         'video',
                                         'image',
                                         'file')})

    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')
    order = OrderField(blank=True, for_fields=['module'])

    class Meta:
        ordering = ['order']


class ItemBase(models.Model):
    owner = models.ForeignKey(User,
                              related_name='%(class)s_related',
                              on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def render(self):
        return render_to_string(
            f'courses/content/{self._meta.model_name}.html',
            {'item': self})

    def __str__(self):
        return self.title


class Text(ItemBase):
    content = models.TextField()


class File(ItemBase):
    file = models.FileField(upload_to='files')


class Image(ItemBase):
    file = models.FileField(upload_to='images')


class Video(ItemBase):
    url = models.URLField()
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    captions_vtt = models.FileField(
        upload_to='captions/', null=True, blank=True,
        help_text='WebVTT captions file.',
    )
    transcript = models.TextField(
        blank=True,
        help_text='Full text transcript for accessibility and search.',
    )
    language = models.CharField(max_length=10, default='en')
