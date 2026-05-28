from datetime import date, timedelta

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import CourseEnrollForm
from django.views.generic.list import ListView
from courses.models import Course, Content, Module
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


class DashboardView(LoginRequiredMixin, TemplateView):
    """Foundry dashboard: metric tiles, continue learning, activity, recommendations."""
    template_name = "students/dashboard.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        enrolled = Course.objects.filter(students=user).select_related("owner", "subject").prefetch_related("modules")
        ctx["metric_enrolled"] = enrolled.count()
        ctx["metric_completed"] = self._count_completed_courses(user, enrolled)
        ctx["metric_streak"] = self._current_streak(user)
        ctx["continue_learning"] = self._continue_learning(user, enrolled)
        ctx["activity_bars"] = self._activity_sparkline(user)
        ctx["recommended"] = self._recommended_for(user, enrolled)
        return ctx

    @staticmethod
    def _count_completed_courses(user, enrolled_qs):
        try:
            from analytics.models import ModuleProgress
        except ImportError:
            return 0
        completed = 0
        for course in enrolled_qs:
            total = course.modules.count()
            if total == 0:
                continue
            done = ModuleProgress.objects.filter(
                user=user, module__course=course, status="completed"
            ).count()
            if done >= total:
                completed += 1
        return completed

    @staticmethod
    def _current_streak(user):
        try:
            from analytics.models import LearningStreak
            return LearningStreak.get_current_streak(user)
        except (ImportError, Exception):
            return 0

    def _continue_learning(self, user, enrolled_qs):
        try:
            from analytics.models import ModuleProgress
        except ImportError:
            return []
        items = []
        recent = (
            ModuleProgress.objects
            .filter(user=user)
            .exclude(status="completed")
            .select_related("module", "module__course")
            .order_by("-last_accessed")[:10]
        )
        seen_course_ids = set()
        for mp in recent:
            course = mp.module.course
            if course.id in seen_course_ids:
                continue
            if user not in course.students.all():
                continue
            seen_course_ids.add(course.id)
            total = course.modules.count() or 1
            done = ModuleProgress.objects.filter(
                user=user, module__course=course, status="completed"
            ).count()
            percent = round((done / total) * 100)
            items.append({
                "course": course,
                "percent": percent,
                "modules_done": done,
                "modules_total": total,
                "next_module": mp.module,
            })
            if len(items) >= 3:
                break
        return items

    @staticmethod
    def _activity_sparkline(user, days=30, max_height=32):
        try:
            from analytics.models import LearningStreak
        except ImportError:
            return []
        end = date.today()
        start = end - timedelta(days=days - 1)
        streaks = {
            s.date: s.modules_completed
            for s in LearningStreak.objects.filter(user=user, date__gte=start, date__lte=end)
        }
        values = [streaks.get(start + timedelta(days=i), 0) for i in range(days)]
        peak = max(values) or 1
        bars = []
        for v in values:
            h = round((v / peak) * max_height) if v else 1
            bars.append({"v": v, "h": h, "y": max_height - h})
        return bars

    @staticmethod
    def _recommended_for(user, enrolled_qs):
        enrolled_ids = list(enrolled_qs.values_list("id", flat=True))
        return (
            Course.objects
            .exclude(id__in=enrolled_ids)
            .select_related("owner", "subject")
            .annotate(module_count=Count("modules"))
            .order_by("-average_rating", "-total_reviews")[:4]
        )


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


# -- M4 Player endpoints ------------------------------------------------------

@login_required
def player_content_view(request, course_id, content_id):
    """HTMX target — returns the rendered content for one item in the player center pane."""
    course = get_object_or_404(Course, id=course_id, students=request.user)
    content = get_object_or_404(Content, id=content_id, module__course=course)
    return render(request, "shared/partials/_player_content.html", {
        "course": course,
        "content": content,
        "module": content.module,
        "item": content.item,
    })


@login_required
@require_POST
def mark_complete_view(request, course_id, module_id):
    """HTMX target — marks a module complete for the user, returns updated progress panel."""
    from analytics.models import ModuleProgress

    course = get_object_or_404(Course, id=course_id, students=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)
    from django.utils import timezone
    mp, _ = ModuleProgress.objects.get_or_create(user=request.user, module=module)
    mp.status = "completed"
    mp.completed_at = mp.completed_at or timezone.now()
    mp.save(update_fields=["status", "completed_at"])

    total = course.modules.count() or 1
    done = ModuleProgress.objects.filter(
        user=request.user, module__course=course, status="completed"
    ).count()
    percent = round((done / total) * 100)

    return render(request, "shared/partials/_progress_panel.html", {
        "course": course,
        "percent": percent,
        "modules_done": done,
        "modules_total": total,
    })
