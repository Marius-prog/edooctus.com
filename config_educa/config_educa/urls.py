from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap

from courses.views import CourseListView, robots_txt
from courses.sitemaps import CourseSitemap, SubjectSitemap, StaticViewSitemap
from honeypot import views as honeypot_views

# Define sitemaps
sitemaps = {
    'courses': CourseSitemap,
    'subjects': SubjectSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(),
         name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(),
         name='logout'),
    path('(K+J+u.dt8/', admin.site.urls),

    # --- Honeypot lures (decoys; real admin is the obfuscated path above) ---
    # Placed before the real `api/` include so the decoy isn't shadowed.
    path('admin/', honeypot_views.fake_admin_login),
    path('wp-login.php', honeypot_views.fake_admin_login),
    path('wp-admin/', honeypot_views.fake_admin_login),
    path('.env', honeypot_views.exposed_file),
    path('backup.sql', honeypot_views.exposed_file),
    path('api/v1/users', honeypot_views.decoy_api_users),
    path('honeypot/', include('honeypot.urls')),

    path('course/', include('courses.urls')),
    path('', CourseListView.as_view(), name='course_list'),
    path('students/', include('students.urls')),
    path('api/', include('courses.api.urls', namespace='api')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('reviews/', include('reviews.urls', namespace='reviews')),
    path('certificates/', include('certificates.urls', namespace='certificates')),
    path('components/', include('shared.urls')),

    # --- New domain apps (Nov 2025) ---
    path('quizzes/', include('quizzes.urls', namespace='quizzes')),
    path('ai/', include('ai_tools.urls', namespace='ai_tools')),
    path('forum/', include('forum.urls', namespace='forum')),
    path('rewards/', include('gamification.urls', namespace='gamification')),
    path('inbox/', include('notifications.urls', namespace='notifications')),
    path('mentorship/', include('mentorship.urls', namespace='mentorship')),
    path('assignments/', include('peer_review.urls', namespace='peer_review')),
    path('privacy/', include('privacy.urls', namespace='privacy')),

    # SEO URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),

]
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
