from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CourseEnrollForm
from django.views.generic.list import ListView
from courses.models import Course
from django.views.generic.detail import DetailView
import redis
from django.conf import settings

# Setting up the Redis connection
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
)


class StudentRegistrationView(CreateView):
    template_name = 'students/student/registration.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('student_course_list')

    def form_valid(self, form):
        result = super().form_valid(form)
        cd = form.cleaned_data
        user = authenticate(username=cd['username'],
                            password=cd['password1'])
        login(self.request, user)
        return result


class StudentEnrollCourseView(LoginRequiredMixin,
                              FormView):
    course = None
    form_class = CourseEnrollForm

    def form_valid(self, form):
        self.course = form.cleaned_data['course']
        self.course.students.add(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('student_course_detail',
                            args=[self.course.id])


class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'students/course/list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(students__in=[self.request.user]).select_related(
            'owner', 'subject'
        ).prefetch_related('modules')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses_with_progress = []
        
        for course in context['object_list']:
            # get last accessed module from Redis
            key = f'student:{self.request.user.id}:course:{course.id}:last_module'
            last_module_id = r.get(key)
            
            course_info = {
                'course': course,
                'last_module': None,
                'progress_text': 'Not started yet'
            }
            
            if last_module_id:
                try:
                    last_module = course.modules.get(id=int(last_module_id))
                    course_info['last_module'] = last_module
                    course_info['progress_text'] = f'Last accessed: {last_module.title}'
                except course.modules.model.DoesNotExist:
                    pass
            
            courses_with_progress.append(course_info)
        
        context['courses_with_progress'] = courses_with_progress
        return context


class StudentCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'students/course/detail.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(students__in=[self.request.user]).select_related(
            'owner', 'subject'
        ).prefetch_related('modules__contents')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # get course object
        course = self.get_object()
        
        if 'module_id' in self.kwargs:
            # get current module
            context['module'] = course.modules.get(
                id=self.kwargs['module_id'])
            # store last accessed module in Redis
            key = f'student:{self.request.user.id}:course:{course.id}:last_module'
            r.set(key, self.kwargs['module_id'])
        else:
            # try to get last accessed module from Redis
            key = f'student:{self.request.user.id}:course:{course.id}:last_module'
            last_module_id = r.get(key)
            
            if last_module_id:
                try:
                    # get the last accessed module
                    context['module'] = course.modules.get(
                        id=int(last_module_id))
                except course.modules.model.DoesNotExist:
                    # if last module doesn't exist, get first module
                    first_module = course.modules.first()
                    if first_module:
                        context['module'] = first_module
            else:
                # get first module if no last accessed module found
                first_module = course.modules.first()
                if first_module:
                    context['module'] = first_module
                    # store first module as last accessed
                    r.set(key, first_module.id)
        
        return context
