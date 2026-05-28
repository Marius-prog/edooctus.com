# Certificates App

Course completion certificate system for the Educto platform.

## Features

### Certificate Management
- Automatic certificate generation upon course completion
- UUID-based certificate IDs for security
- Unique verification codes for public validation
- Certificate download tracking
- Certificate revocation system

### Models

#### Certificate
- **user**: ForeignKey to User (certificate recipient)
- **course**: ForeignKey to Course
- **certificate_id**: UUID (unique identifier)
- **verification_code**: Unique 12-character code for verification
- **issued_at**: DateTime of certificate issuance
- **completion_date**: Date of course completion
- **grade**: Optional grade field (e.g., "A", "Pass")
- **is_valid**: Boolean for certificate status
- **revoked_at**: DateTime of revocation (if applicable)
- **revoked_reason**: Text explaining revocation
- **download_count**: Track number of downloads
- **last_downloaded**: DateTime of last download

#### CertificateTemplate
- **name**: Template name
- **description**: Template description
- **html_template**: HTML template with Django template placeholders
- **css_styles**: CSS styling for certificate
- **is_default**: Only one default template allowed
- **created_at**: Template creation date
- **updated_at**: Last update date

### Views

#### request_certificate
- **URL**: `/certificates/request/<course_id>/`
- **Authentication**: Required (login_required)
- **Function**: Request certificate for completed course
- **Validation**:
  - User must be enrolled in course
  - All course modules must be completed
- **Behavior**: Creates certificate if doesn't exist, redirects to view

#### view_certificate
- **URL**: `/certificates/view/<certificate_id>/`
- **Authentication**: Required (login_required)
- **Function**: Display certificate as HTML
- **Security**: Only certificate owner can view
- **Output**: Rendered HTML certificate

#### download_certificate
- **URL**: `/certificates/download/<certificate_id>/`
- **Authentication**: Required (login_required)
- **Function**: Download certificate (currently as HTML)
- **Behavior**: Tracks download count
- **Note**: Users can use browser's "Print > Save as PDF" feature

#### verify_certificate
- **URL**: `/certificates/verify/<verification_code>/`
- **Authentication**: Public (no login required)
- **Function**: Public verification page for certificates
- **Output**: Certificate validity status and details

#### my_certificates
- **URL**: `/certificates/my/`
- **Authentication**: Required (login_required)
- **Function**: List all user's certificates
- **Display**: Grid of certificate cards with view/download actions

### Utility Functions

#### check_course_completion(user, course)
Checks if user has completed all modules in a course by querying ModuleProgress records.

**Returns**: Boolean

#### generate_certificate_html(certificate, template=None)
Generates HTML for certificate using template system.

**Parameters**:
- certificate: Certificate instance
- template: Optional CertificateTemplate instance

**Returns**: Complete HTML document as string

#### get_default_template()
Returns or creates the default certificate template.

**Returns**: CertificateTemplate instance

### Admin Interface

#### CertificateAdmin
- List display: user, course, certificate_id, issued_at, is_valid, download_count
- Filters: is_valid, issued_at
- Search: username, course title, certificate_id, verification_code
- Actions: Bulk revoke certificates
- Date hierarchy: issued_at

#### CertificateTemplateAdmin
- List display: name, is_default, created_at
- Filters: is_default
- Search: name, description

## Installation

### 1. Add to INSTALLED_APPS
Already added to `config_educa/settings/base.py`:
```python
INSTALLED_APPS = [
    # ...
    'certificates.apps.CertificatesConfig',  # Course Certificates
]
```

### 2. Add URLs
Already added to `config_educa/urls.py`:
```python
urlpatterns = [
    # ...
    path('certificates/', include('certificates.urls', namespace='certificates')),
]
```

### 3. Run Migrations
```bash
cd config_educa
python manage.py migrate certificates
```

## Usage

### For Students

1. **Complete all course modules** - Progress tracked via analytics app
2. **Request certificate** - Visit course detail page and click "Request Certificate"
3. **View certificate** - Access from "My Certificates" page
4. **Download certificate** - Click download button, use browser's Print to PDF

### For Instructors/Admins

1. **Manage certificates** - Access via Django admin at `/(K+J+u.dt8/`
2. **Create custom templates** - Add new CertificateTemplate in admin
3. **Revoke certificates** - Use admin action or call `certificate.revoke(reason)`

### Public Verification

Anyone can verify a certificate at:
```
/certificates/verify/<verification_code>/
```

## Templates

### Default Certificate Template

The default template includes:
- Professional border design
- Student name (prominently displayed)
- Course title
- Instructor name
- Completion date
- Certificate ID and verification code
- Blue color scheme (#3B82F6, #1E40AF)

### Custom Templates

Create custom templates in the admin panel using:
- **HTML placeholders**: `{{ user }}`, `{{ course }}`, `{{ issued_date }}`, etc.
- **CSS styling**: Full custom CSS support
- **Multiple templates**: Switch between templates per certificate

## Integration with Other Apps

### Analytics App
- Uses `ModuleProgress` model to check course completion
- Tracks which modules student has completed

### Courses App
- Links to `Course` model
- Uses course owner as instructor

### Students App
- Displays certificates in student dashboard (integration needed)
- Shows certificate request button on completed courses

## Security Features

1. **UUID Certificate IDs** - Unique, non-sequential identifiers
2. **Verification Codes** - 12-character alphanumeric codes
3. **Owner Verification** - Only certificate owner can view/download
4. **Revocation System** - Certificates can be revoked with reason
5. **Download Tracking** - Monitor certificate usage

## Future Enhancements

1. **PDF Generation** - Use ReportLab or WeasyPrint for true PDF output
2. **Email Delivery** - Auto-email certificates on completion
3. **LinkedIn Integration** - Share certificates to LinkedIn
4. **QR Codes** - Add QR code linking to verification page
5. **Certificate Analytics** - Track views, downloads, verifications
6. **Bulk Generation** - Admin tool to generate certificates for cohorts
7. **Digital Signatures** - Cryptographic signing of certificates

## Testing

Run tests:
```bash
python manage.py test certificates
```

Test coverage includes:
- Certificate creation and validation
- Verification code uniqueness
- Certificate revocation
- Download tracking
- Course completion checking
- Template management

## Files Structure

```
certificates/
├── __init__.py
├── admin.py              # Admin interface configuration
├── apps.py               # App configuration
├── models.py             # Certificate and CertificateTemplate models
├── views.py              # Certificate views
├── urls.py               # URL routing
├── utils.py              # Utility functions
├── tests.py              # Unit tests
├── README.md             # This file
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py   # Initial migration
└── templates/
    └── certificates/
        ├── verify.html          # Public verification page
        └── my_certificates.html # User certificate list
```

## Dependencies

- Django 4.2+
- courses app (for Course model)
- analytics app (for ModuleProgress)
- Django contrib.auth (for User model)

## API Endpoints

Currently the app uses traditional Django views. REST API endpoints can be added:

Potential endpoints:
- `GET /api/certificates/` - List user's certificates
- `POST /api/certificates/<course_id>/request/` - Request certificate
- `GET /api/certificates/<certificate_id>/` - Certificate details
- `GET /api/certificates/verify/<code>/` - Verify certificate

## Environment Variables

None required. Uses Django settings from project.

## Support

For issues or questions, contact the development team or file an issue in the repository.
