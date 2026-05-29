from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "quizzes"

router = DefaultRouter()
router.register(r"quizzes", views.QuizViewSet, basename="quiz")
router.register(r"submissions", views.SubmissionViewSet, basename="submission")

urlpatterns = [
    path("", views.QuizListView.as_view(), name="list"),
    path("<int:pk>/", views.QuizDetailView.as_view(), name="detail"),
    path("<int:pk>/take/", views.quiz_take, name="take"),
    path("api/", include(router.urls)),
]
