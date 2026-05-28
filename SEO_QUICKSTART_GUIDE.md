# SEO Quick-Start Implementation Guide
## Get Your First SEO Improvements Live in 2 Hours

---

## STEP 1: INSTALL DJANGO-META (15 minutes)

```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio/config_educa

# Activate virtual environment
source venv/bin/activate

# Install django-meta
pip install django-meta

# Update requirements.txt
pip freeze > ../requirements.txt
```

**Update settings:**
```python
# config_educa/config_educa/settings/base.py

INSTALLED_APPS = [
    'courses.apps.CoursesConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'meta',  # ADD THIS LINE
    'django_extensions',
    # ... rest of apps
]
```

---

## STEP 2: UPDATE BASE TEMPLATE (20 minutes)

**Replace:** `config_educa/courses/templates/base.html`

```django
{% load static %}
{% load meta %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    {# Meta tags from django-meta #}
    {% include 'meta/meta.html' %}

    <title>{% block title %}{% if meta_title %}{{ meta_title }}{% else %}Educto.io - Learn Online Courses{% endif %}{% endblock %}</title>

    {# Canonical URL #}
    <link rel="canonical" href="https://www.educto.io{{ request.path }}">

    {# Language #}
    <link rel="alternate" hreflang="en" href="https://www.educto.io{{ request.path }}" />
    <link rel="alternate" hreflang="x-default" href="https://www.educto.io{{ request.path }}" />

    {# CSS #}
    <link href="{% static 'css/base.css' %}" rel="stylesheet">
</head>
<body>
<div id="header">
    <a href="/" class="logo">Educto.io</a>
    <ul class="menu">
        {% if request.user.is_authenticated %}
        <li><a href="{% url 'logout' %}">Sign out</a></li>
        {% else %}
        <li><a href="{% url 'login' %}">Sign in</a></li>
        {% endif %}
    </ul>
</div>
<div id="content">
    {% block content %}
    {% endblock %}
</div>
{% block include_js %}
{% endblock %}
<script>
      document.addEventListener('DOMContentLoaded', (event) => {
        // DOM loaded
        {% block domready %}
        {% endblock %}
      })
</script>
</body>
</html>
```

---

## STEP 3: ADD META FIELDS TO COURSE MODEL (30 minutes)

**Update:** `config_educa/courses/models.py`

```python
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .fields import OrderField
from django.template.loader import render_to_string
from meta.models import ModelMeta  # ADD THIS

class Subject(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Course(ModelMeta, models.Model):  # ADD ModelMeta HERE
    owner = models.ForeignKey(User,
                              related_name='courses_created',
                              on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject,
                                related_name='courses',
                                on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    overview = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    students = models.ManyToManyField(User,
                                      related_name='courses_joined',
                                      blank=True)

    # ADD THESE METADATA SETTINGS
    _metadata = {
        'title': 'get_meta_title',
        'description': 'get_meta_description',
        'keywords': 'get_meta_keywords',
    }

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created']),
            models.Index(fields=['owner', '-created']),
            models.Index(fields=['subject', '-created']),
        ]

    # ADD THESE METHODS
    def get_meta_title(self):
        """Generate SEO-optimized title (max 60 chars)"""
        return f"{self.title} | Learn Online at Educto.io"

    def get_meta_description(self):
        """Generate SEO-optimized description (max 160 chars)"""
        description = self.overview[:140]
        instructor = self.owner.get_full_name() or self.owner.username
        return f"{description}... Taught by {instructor}. Enroll now!"

    def get_meta_keywords(self):
        """Generate relevant keywords"""
        return [
            self.title,
            self.subject.title,
            f"{self.subject.title} course",
            "online learning",
            "online education",
        ]

    def __str__(self):
        return self.title

# Keep rest of models unchanged (Module, Content, ItemBase, etc.)
```

**Create migration:**
```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio/config_educa
python manage.py makemigrations
python manage.py migrate
```

---

## STEP 4: CREATE ROBOTS.TXT (10 minutes)

**Create:** `config_educa/courses/views.py` (add this function)

```python
from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def robots_txt(request):
    """Serve robots.txt file"""
    lines = [
        "User-agent: *",
        "Disallow: /(K+J+u.dt8/",  # Admin
        "Disallow: /api/",
        "Disallow: /chat/",
        "Disallow: /students/enroll-course/",
        "Disallow: /accounts/",
        "Allow: /course/",
        "",
        "Sitemap: https://www.educto.io/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
```

**Update:** `config_educa/config_educa/urls.py`

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from courses.views import CourseListView, robots_txt  # ADD robots_txt

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('(K+J+u.dt8/', admin.site.urls),
    path('course/', include('courses.urls')),
    path('', CourseListView.as_view(), name='course_list'),
    path('students/', include('students.urls')),
    path('api/', include('courses.api.urls', namespace='api')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('__debug__/', include('debug_toolbar.urls')),
    path('robots.txt', robots_txt),  # ADD THIS LINE
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
```

---

## STEP 5: CREATE SITEMAP (30 minutes)

**Create file:** `config_educa/courses/sitemaps.py`

```python
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Course, Subject

class CourseSitemap(Sitemap):
    """Sitemap for course detail pages"""
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Course.objects.all()

    def lastmod(self, obj):
        return obj.created

    def location(self, obj):
        return f'/course/{obj.slug}/'


class SubjectSitemap(Sitemap):
    """Sitemap for subject category pages"""
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        return Subject.objects.all()

    def location(self, obj):
        return f'/course/subject/{obj.slug}/'


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = 'monthly'

    def items(self):
        return ['course_list']

    def location(self, item):
        return reverse(item)
```

**Update settings:** `config_educa/config_educa/settings/base.py`

```python
INSTALLED_APPS = [
    'courses.apps.CoursesConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',  # ADD THIS
    'meta',
    # ... rest
]
```

**Update URLs:** `config_educa/config_educa/urls.py`

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap  # ADD THIS

from courses.views import CourseListView, robots_txt
from courses.sitemaps import CourseSitemap, SubjectSitemap, StaticViewSitemap  # ADD THIS

# Define sitemaps
sitemaps = {
    'courses': CourseSitemap,
    'subjects': SubjectSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('(K+J+u.dt8/', admin.site.urls),
    path('course/', include('courses.urls')),
    path('', CourseListView.as_view(), name='course_list'),
    path('students/', include('students.urls')),
    path('api/', include('courses.api.urls', namespace='api')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('__debug__/', include('debug_toolbar.urls')),
    path('robots.txt', robots_txt),

    # ADD THIS LINE
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
```

---

## STEP 6: TEST YOUR CHANGES (15 minutes)

```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio/config_educa

# Start development server
python manage.py runserver
```

**Test these URLs:**

1. **Homepage meta tags:**
   - Visit: http://127.0.0.1:8000/
   - View source, check for `<meta>` tags

2. **Course detail meta tags:**
   - Visit any course: http://127.0.0.1:8000/course/[course-slug]/
   - View source, check for course-specific meta tags

3. **Robots.txt:**
   - Visit: http://127.0.0.1:8000/robots.txt
   - Should see disallow rules and sitemap URL

4. **Sitemap:**
   - Visit: http://127.0.0.1:8000/sitemap.xml
   - Should see XML with all course URLs

---

## STEP 7: ADD STRUCTURED DATA (30 minutes)

**Update Course model:** `config_educa/courses/models.py`

Add this method to the Course class:

```python
import json

class Course(ModelMeta, models.Model):
    # ... existing fields and methods ...

    def get_structured_data(self):
        """Generate Course structured data in JSON-LD format"""
        instructor = self.owner
        instructor_name = instructor.get_full_name() or instructor.username

        structured_data = {
            "@context": "https://schema.org",
            "@type": "Course",
            "name": self.title,
            "description": self.overview,
            "url": f"https://www.educto.io/course/{self.slug}/",
            "provider": {
                "@type": "Organization",
                "name": "Educto.io",
                "sameAs": "https://www.educto.io",
                "url": "https://www.educto.io"
            },
            "instructor": {
                "@type": "Person",
                "name": instructor_name,
            },
            "teaches": self.subject.title,
            "inLanguage": "en",
            "datePublished": self.created.isoformat(),
        }

        return json.dumps(structured_data, indent=2)
```

**Update course detail template:**

Find: `config_educa/courses/templates/courses/course/detail.html`

Add this at the top of the content block:

```django
{% extends "base.html" %}

{% block title %}
{{ course.title }} - Learn Online at Educto.io
{% endblock %}

{% block content %}
{# ADD THIS STRUCTURED DATA #}
<script type="application/ld+json">
{{ course.get_structured_data|safe }}
</script>

{# Rest of your template below #}
<h1>{{ course.title }}</h1>
<!-- ... existing content ... -->
{% endblock %}
```

---

## STEP 8: VALIDATION (10 minutes)

### Validate Meta Tags:
1. Visit course page: http://127.0.0.1:8000/course/[slug]/
2. View page source (Ctrl+U / Cmd+Option+U)
3. Check for:
   - `<title>` tag with course name
   - `<meta name="description">` with course overview
   - `<meta name="keywords">` with relevant keywords
   - `<link rel="canonical">` with correct URL

### Validate Structured Data:
1. Copy the `<script type="application/ld+json">` content
2. Go to: https://validator.schema.org/
3. Paste JSON-LD
4. Click "Run Test"
5. Should show no errors

### Validate Sitemap:
1. Visit: http://127.0.0.1:8000/sitemap.xml
2. Should see all course URLs
3. Copy sitemap XML
4. Go to: https://www.xml-sitemaps.com/validate-xml-sitemap.html
5. Paste and validate

---

## STEP 9: DEPLOY TO PRODUCTION (If Ready)

```bash
# Commit changes
cd /Users/mariussabaliauskas/Documents/Programming/eductoio
git add .
git commit -m "Add SEO: meta tags, structured data, sitemap, robots.txt"
git push

# If using Docker:
docker-compose down
docker-compose up -d --build

# Run migrations in production
docker-compose exec web python config_educa/manage.py migrate

# Collect static files
docker-compose exec web python config_educa/manage.py collectstatic --noinput
```

---

## STEP 10: SUBMIT TO GOOGLE (15 minutes)

### Google Search Console:

1. **Sign up:** https://search.google.com/search-console
2. **Add property:** www.educto.io
3. **Verify ownership:** Upload HTML file or add meta tag
4. **Submit sitemap:**
   - Go to Sitemaps section
   - Add: `https://www.educto.io/sitemap.xml`
   - Click Submit

### Monitor:

- **Indexing:** Check "Coverage" report daily
- **Performance:** Check "Performance" report weekly
- **Errors:** Fix any crawl errors immediately

---

## VERIFICATION CHECKLIST

After completing all steps, verify:

- [ ] Meta tags appear on all pages (view source)
- [ ] Course structured data validates (schema.org validator)
- [ ] Sitemap.xml is accessible and contains all URLs
- [ ] Robots.txt is accessible and has correct rules
- [ ] Canonical URLs point to https://www.educto.io
- [ ] No console errors in browser
- [ ] All existing functionality still works
- [ ] Sitemap submitted to Google Search Console

---

## EXPECTED RESULTS

### Immediately:
- Meta tags appear in search results (1-2 weeks)
- Sitemap indexed by Google (3-7 days)
- Course pages start appearing in search

### Within 1 Month:
- 20-30% increase in indexed pages
- Better click-through rates from search
- Rich snippets may start appearing

### Within 3 Months:
- 50-100% increase in organic traffic
- Improved rankings for course keywords
- More course enrollments from search

---

## TROUBLESHOOTING

### Meta tags not showing:
- Check if django-meta is in INSTALLED_APPS
- Verify `{% load meta %}` is in base.html
- Check `{% include 'meta/meta.html' %}` is present

### Sitemap errors:
- Verify django.contrib.sitemaps in INSTALLED_APPS
- Check sitemap imports in urls.py
- Test URL: http://127.0.0.1:8000/sitemap.xml

### Structured data validation fails:
- Validate JSON at https://jsonlint.com/
- Check for missing quotes or commas
- Ensure dates are in ISO format

### Robots.txt not accessible:
- Check robots_txt function in views.py
- Verify URL pattern in urls.py
- Test: http://127.0.0.1:8000/robots.txt

---

## NEXT STEPS

After this quick-start implementation:

1. **Add performance optimization** (compression, caching)
2. **Implement breadcrumbs** for better navigation
3. **Add FAQ schema** to course pages
4. **Create review/rating system**
5. **Set up Core Web Vitals monitoring**

**See full audit for complete implementation:**
`/Users/mariussabaliauskas/Documents/Programming/eductoio/SEO_AUDIT_REPORT_2025.md`

---

## TIME BREAKDOWN

- Step 1 (Install): 15 min
- Step 2 (Template): 20 min
- Step 3 (Model): 30 min
- Step 4 (Robots): 10 min
- Step 5 (Sitemap): 30 min
- Step 6 (Testing): 15 min
- Step 7 (Structured Data): 30 min
- Step 8 (Validation): 10 min
- Step 9 (Deploy): 15 min
- Step 10 (Google): 15 min

**Total Time: ~3 hours** (including testing and validation)

---

**Questions?** Refer to the full SEO audit report for detailed explanations and additional implementations.

*Generated: October 23, 2025*
