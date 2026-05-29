from rest_framework import serializers
from .models import Quiz, Question, Choice, Submission, Answer, Rubric, RubricCriterion


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "order"]  # is_correct intentionally omitted from API


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "prompt", "question_type", "points", "order", "choices"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    total_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "course", "module", "title", "description", "pass_mark_pct",
                  "time_limit_seconds", "max_attempts", "grading_mode", "is_published",
                  "total_points", "questions"]


class AnswerSerializer(serializers.ModelSerializer):
    selected_choice_ids = serializers.PrimaryKeyRelatedField(
        queryset=Choice.objects.all(), many=True, write_only=True, required=False,
        source="selected_choices",
    )

    class Meta:
        model = Answer
        fields = ["id", "question", "selected_choice_ids", "text_response", "awarded_points"]
        read_only_fields = ["awarded_points"]


class SubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "quiz", "user", "started_at", "submitted_at",
                  "score_points", "score_pct", "passed", "status", "answers"]
        read_only_fields = ["score_points", "score_pct", "passed", "status",
                            "submitted_at", "user"]


class RubricCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubricCriterion
        fields = ["id", "criterion", "max_points", "order"]


class RubricSerializer(serializers.ModelSerializer):
    criteria = RubricCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = Rubric
        fields = ["id", "name", "description", "criteria"]
