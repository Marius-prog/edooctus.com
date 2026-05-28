from django.urls import path
from . import views
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('dashboard/',
         views.DashboardView.as_view(),
         name='dashboard'),
    path('register/',
         views.StudentRegistrationView.as_view(),
         name='student_registration'),
    path('enroll-course/',
         views.StudentEnrollCourseView.as_view(),
         name='student_enroll_course'),
    path('courses/',
         views.StudentCourseListView.as_view(),
         name='student_course_list'),
    path('course/<pk>/',
         cache_page(60 * 15)(views.StudentCourseDetailView.as_view()),
         name='student_course_detail'),
    path('course/<pk>/<module_id>/',
         cache_page(60 * 15)(views.StudentCourseDetailView.as_view()),
         name='student_course_detail_module'),
    path('course/<int:course_id>/content/<int:content_id>/',
         views.player_content_view,
         name='player_content'),
    path('course/<int:course_id>/module/<int:module_id>/complete/',
         views.mark_complete_view,
         name='mark_complete'),

]
