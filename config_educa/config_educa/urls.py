from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap

from courses.views import CourseListView, robots_txt
from courses.sitemaps import CourseSitemap, SubjectSitemap, StaticViewSitemap

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
    path('course/', include('courses.urls')),
    path('', CourseListView.as_view(), name='course_list'),
    path('students/', include('students.urls')),
    path('api/', include('courses.api.urls', namespace='api')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('reviews/', include('reviews.urls', namespace='reviews')),
    path('certificates/', include('certificates.urls', namespace='certificates')),
    path('__debug__/', include('debug_toolbar.urls')),
    path('components/', include('shared.urls')),

    # SEO URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)



def replace_entities(text):
    doc = nlp(text)
    replaced_text = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            hash_value = hashlib.sha256(ent.text.encode()).hexdigest()[:8]
            replaced_text.append(hash_value)
        else:
        
#             replaced_text.append(ent.text)
#             stars = "*** not full name ***"
            replaced_text.append("*** not full name ***")
        return " ".join(replaced_text)