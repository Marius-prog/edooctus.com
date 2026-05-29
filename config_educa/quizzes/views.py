from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, View
from django.http import JsonResponse

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Quiz, Submission, Answer
from .serializers import QuizSerializer, SubmissionSerializer, AnswerSerializer


def user_can_attempt(user, quiz) -> bool:
    """A user may attempt a quiz only if they own or are enrolled in its course."""
    return (quiz.course.owner_id == user.id
            or quiz.course.students.filter(id=user.id).exists())


# -- DRF API ------------------------------------------------------------------

class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Quiz.objects.filter(is_published=True).prefetch_related("questions__choices")
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        quiz = self.get_object()
        if not user_can_attempt(request.user, quiz):
            return Response({"detail": "You are not enrolled in this course."},
                            status=status.HTTP_403_FORBIDDEN)
        prior = Submission.objects.filter(quiz=quiz, user=request.user).count()
        if prior >= quiz.max_attempts:
            return Response({"detail": "Max attempts reached."},
                            status=status.HTTP_403_FORBIDDEN)
        sub = Submission.objects.create(quiz=quiz, user=request.user)
        return Response(SubmissionSerializer(sub).data, status=status.HTTP_201_CREATED)


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).prefetch_related("answers")

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        sub = self.get_object()
        if sub.status != Submission.STATUS_IN_PROGRESS:
            return Response({"detail": "Submission already finalized."},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = AnswerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        question = ser.validated_data["question"]
        if question.quiz_id != sub.quiz_id:
            return Response({"detail": "Question does not belong to this quiz."},
                            status=status.HTTP_400_BAD_REQUEST)
        choices = ser.validated_data.get("selected_choices", [])
        if any(c.question_id != question.id for c in choices):
            return Response({"detail": "Choice does not belong to the question."},
                            status=status.HTTP_400_BAD_REQUEST)
        ans, _ = Answer.objects.update_or_create(
            submission=sub, question=question,
            defaults={"text_response": ser.validated_data.get("text_response", "")},
        )
        if "selected_choices" in ser.validated_data:
            ans.selected_choices.set(choices)
        return Response(AnswerSerializer(ans).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        sub = self.get_object()
        if sub.status != Submission.STATUS_IN_PROGRESS:
            return Response({"detail": "Submission already finalized."},
                            status=status.HTTP_400_BAD_REQUEST)
        sub.grade()
        return Response(SubmissionSerializer(sub).data)


# -- Server-rendered ----------------------------------------------------------

class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    template_name = "quizzes/list.html"

    def get_queryset(self):
        return Quiz.objects.filter(is_published=True).select_related("course")


class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = "quizzes/detail.html"
    context_object_name = "quiz"

    def get_queryset(self):
        return Quiz.objects.filter(is_published=True).prefetch_related("questions__choices")


@login_required
@require_POST
def quiz_take(request, pk):
    """HTMX form handler: ingest a full attempt and render the result partial."""
    from .models import Choice
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)

    if not user_can_attempt(request.user, quiz):
        return render(request, "quizzes/_result.html",
                      {"error": "You are not enrolled in this course."}, status=403)

    prior_attempts = Submission.objects.filter(quiz=quiz, user=request.user).count()
    if prior_attempts >= quiz.max_attempts:
        return render(request, "quizzes/_result.html",
                      {"error": "Max attempts reached."}, status=403)

    sub = Submission.objects.create(quiz=quiz, user=request.user)
    for q in quiz.questions.prefetch_related("choices"):
        if q.question_type == "short":
            text = (request.POST.get(f"q_{q.id}_text") or "").strip()
            Answer.objects.create(submission=sub, question=q, text_response=text)
        else:
            ids = request.POST.getlist(f"q_{q.id}")
            ans = Answer.objects.create(submission=sub, question=q)
            if ids:
                ans.selected_choices.set(Choice.objects.filter(id__in=ids, question=q))
    sub.grade()
    return render(request, "quizzes/_result.html",
                  {"submission": sub, "quiz": quiz})
