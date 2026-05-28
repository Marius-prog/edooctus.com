from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('add/<int:course_id>/', views.add_review, name='add_review'),
    path('helpful/<int:review_id>/', views.mark_helpful, name='mark_helpful'),
]
