# Certificate System Installation Guide

## Status: Implementation Complete ✓

All code has been implemented. Follow these steps to activate the certificate system.

## Files Created

### Core Files
- ✓ `/config_educa/certificates/__init__.py` - Package initialization
- ✓ `/config_educa/certificates/apps.py` - Django app configuration
- ✓ `/config_educa/certificates/models.py` - Certificate and CertificateTemplate models
- ✓ `/config_educa/certificates/views.py` - All views (request, view, download, verify, my_certificates)
- ✓ `/config_educa/certificates/urls.py` - URL routing
- ✓ `/config_educa/certificates/admin.py` - Django admin configuration
- ✓ `/config_educa/certificates/utils.py` - Utility functions
- ✓ `/config_educa/certificates/tests.py` - Unit tests

### Migrations
- ✓ `/config_educa/certificates/migrations/__init__.py`
- ✓ `/config_educa/certificates/migrations/0001_initial.py` - Initial migration

### Templates
- ✓ `/config_educa/certificates/templates/certificates/verify.html` - Public verification page
- ✓ `/config_educa/certificates/templates/certificates/my_certificates.html` - User certificate list

### Documentation
- ✓ `/config_educa/certificates/README.md` - Complete documentation
- ✓ `/config_educa/certificates/INSTALLATION.md` - This file

## Configuration Changes

### Settings (ALREADY UPDATED)
✓ Added to `/config_educa/config_educa/settings/base.py`:
```python
INSTALLED_APPS = [
    # ...
    'certificates.apps.CertificatesConfig',  # Course Certificates
]
```

### URLs (ALREADY UPDATED)
✓ Added to `/config_educa/config_educa/urls.py`:
```python
urlpatterns = [
    # ...
    path('certificates/', include('certificates.urls', namespace='certificates')),
]
```

## Next Steps

### 1. Activate Virtual Environment
```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio
source venv/bin/activate
```

If the virtual environment has Python path issues, you may need to recreate it:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
cd config_educa
python manage.py migrate certificates
```

This will create the database tables:
- `certificates_certificate`
- `certificates_certificatetemplate`

### 3. Create Default Template
The default template will be created automatically on first use. To create it manually:
```bash
python manage.py shell
```
```python
from certificates.utils import get_default_template
template = get_default_template()
print(f"Created template: {template.name}")
```

### 4. Verify Installation
```bash
# Check that app is recognized
python manage.py check certificates

# Run tests
python manage.py test certificates

# Start development server
python manage.py runserver
```

### 5. Access Admin Interface
1. Visit: `http://localhost:8000/(K+J+u.dt8/`
2. Login with superuser credentials
3. Navigate to "Certificates" section
4. You should see:
   - Certificates
   - Certificate Templates

## URL Endpoints Available

After installation, these URLs will be active:

### Student URLs (login required)
- `/certificates/request/<course_id>/` - Request certificate for completed course
- `/certificates/view/<certificate_id>/` - View your certificate
- `/certificates/download/<certificate_id>/` - Download your certificate
- `/certificates/my/` - View all your certificates

### Public URLs (no login required)
- `/certificates/verify/<verification_code>/` - Verify certificate authenticity

## Testing the System

### As a Student

1. **Complete a course**:
   - Enroll in a course
   - Complete all modules (tracked in analytics app)
   - Check that all ModuleProgress records show "completed"

2. **Request certificate**:
   ```
   Visit: /certificates/request/<course_id>/
   ```

3. **View your certificates**:
   ```
   Visit: /certificates/my/
   ```

### As an Admin

1. **Access admin panel**:
   ```
   Visit: http://localhost:8000/(K+J+u.dt8/
   ```

2. **View certificates**:
   - Click on "Certificates" under "Certificates" section
   - Search, filter, and manage certificates

3. **Create custom template**:
   - Click on "Certificate Templates"
   - Add new template with custom HTML/CSS
   - Mark as default if desired

### Public Verification

Anyone can verify a certificate:
1. Get verification code from certificate
2. Visit: `/certificates/verify/<verification_code>/`
3. View certificate details and validity status

## Integration with Existing Apps

### Required Integration Points

#### 1. Student Dashboard
Add certificate button to completed courses in `students/templates/students/course/list.html`:

```html
{% if course is completed %}
    <a href="{% url 'certificates:request_certificate' course.id %}">
        Request Certificate
    </a>
{% endif %}
```

#### 2. Course Detail Page
Add certificate request option in course detail view for enrolled students.

#### 3. Navigation Menu
Add "My Certificates" link to user menu:
```html
<a href="{% url 'certificates:my_certificates' %}">My Certificates</a>
```

## Troubleshooting

### Migration Issues

If migrations fail:
```bash
# Check migrations status
python manage.py showmigrations certificates

# If needed, fake the initial migration
python manage.py migrate certificates --fake-initial
```

### Virtual Environment Issues

If you encounter "No module named 'django'" or Python version errors:
```bash
# Deactivate current venv
deactivate

# Remove old venv
rm -rf venv

# Create new venv with system Python
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install django==4.2
pip install channels
pip install channels-redis
# ... install other dependencies
```

### Template Not Found Errors

Ensure templates are in correct location:
```
config_educa/certificates/templates/certificates/
├── verify.html
└── my_certificates.html
```

### Import Errors

If you see import errors for analytics or courses:
```bash
# Check that these apps are installed
python manage.py check

# Verify in settings
python manage.py shell
>>> from django.conf import settings
>>> 'analytics' in settings.INSTALLED_APPS
>>> 'courses' in settings.INSTALLED_APPS
```

## Environment Considerations

### Development (SQLite)
The certificate system works with SQLite for local development.

### Production (PostgreSQL)
The migration file is compatible with PostgreSQL. Run migrations in production:
```bash
# In production environment
python manage.py migrate certificates
```

### Redis
Not required for basic certificate functionality (Redis is used for chat/caching).

## Success Indicators

You'll know the installation is successful when:

1. ✓ `python manage.py check certificates` shows no errors
2. ✓ Migrations run without errors
3. ✓ Certificate models appear in Django admin
4. ✓ All URL endpoints return 200 (when authenticated)
5. ✓ Tests pass: `python manage.py test certificates`
6. ✓ Default template is created
7. ✓ Students can request and view certificates

## Support

If you encounter issues:

1. Check Django logs for error messages
2. Verify all dependencies are installed
3. Ensure analytics app is working (ModuleProgress tracking)
4. Check that courses have modules defined
5. Verify user enrollment in courses

## Next Development Steps

After installation, consider:

1. **Add PDF generation** - Install WeasyPrint or ReportLab
2. **Email notifications** - Send certificates via email
3. **UI improvements** - Add certificate badges, social sharing
4. **LinkedIn integration** - Allow sharing to LinkedIn
5. **Analytics dashboard** - Track certificate statistics
6. **Bulk operations** - Generate certificates for entire cohorts

## Deployment Notes

When deploying to production:

1. Run migrations on production database
2. Collect static files: `python manage.py collectstatic`
3. Restart web server (uWSGI)
4. Verify certificate URLs in production
5. Test public verification page
6. Configure email backend for certificate delivery (future feature)

---

**Installation Complete!** 🎓

The certificate system is fully implemented and ready for use. Follow the steps above to activate it in your environment.
