from django.contrib import admin
from .models import Quiz, Question, Choice, Submission, Rubric, RubricCriterion


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "is_published", "pass_mark_pct", "max_attempts", "created")
    list_filter = ("is_published", "grading_mode", "course")
    search_fields = ("title", "course__title")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "quiz", "question_type", "points", "order")
    list_filter = ("question_type", "quiz")
    inlines = [ChoiceInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "status", "score_pct", "passed", "started_at")
    list_filter = ("status", "passed", "quiz")
    readonly_fields = ("score_points", "score_pct", "passed")


class RubricCriterionInline(admin.TabularInline):
    model = RubricCriterion
    extra = 1


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ("name", "created")
    inlines = [RubricCriterionInline]
