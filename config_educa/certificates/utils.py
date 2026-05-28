from django.template import Template, Context
from django.utils import timezone


def check_course_completion(user, course):
    """Check if user has completed all modules in a course"""
    from analytics.models import ModuleProgress

    total_modules = course.modules.count()
    if total_modules == 0:
        return False

    completed_modules = ModuleProgress.objects.filter(
        user=user,
        module__course=course,
        status='completed'
    ).count()

    return completed_modules == total_modules


def generate_certificate_html(certificate, template=None):
    """Generate HTML for certificate"""
    from .models import CertificateTemplate

    if not template:
        template = CertificateTemplate.objects.filter(is_default=True).first()
        if not template:
            template = get_default_template()

    html_template = Template(template.html_template)
    css_styles = template.css_styles

    context = Context({
        'user': certificate.user,
        'course': certificate.course,
        'certificate': certificate,
        'issued_date': certificate.issued_at.strftime('%B %d, %Y'),
        'instructor': certificate.course.owner,
        'verification_code': certificate.verification_code,
        'certificate_id': certificate.certificate_id,
    })

    html_content = html_template.render(context)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Certificate of Completion</title>
        <style>
            {css_styles}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """


def get_default_template():
    """Return default certificate template"""
    from .models import CertificateTemplate

    default_html = """
    <div class="certificate">
        <div class="border">
            <div class="content">
                <h1>Certificate of Completion</h1>
                <p class="subtitle">This is to certify that</p>
                <h2 class="student-name">{{ user.get_full_name|default:user.username }}</h2>
                <p class="subtitle">has successfully completed</p>
                <h3 class="course-title">{{ course.title }}</h3>
                <p class="course-info">
                    Instructed by {{ instructor.get_full_name|default:instructor.username }}
                </p>
                <div class="details">
                    <div class="date">
                        <p>Date of Completion</p>
                        <p class="value">{{ issued_date }}</p>
                    </div>
                    <div class="signature">
                        <p>Instructor Signature</p>
                        <p class="value">{{ instructor.get_full_name|default:instructor.username }}</p>
                    </div>
                </div>
                <p class="verification">
                    Certificate ID: {{ certificate_id }}<br>
                    Verification Code: {{ verification_code }}
                </p>
            </div>
        </div>
    </div>
    """

    default_css = """
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    body {
        font-family: 'Georgia', serif;
        padding: 40px;
        background: #f5f5f5;
    }
    .certificate {
        width: 1000px;
        margin: 0 auto;
        background: white;
        padding: 60px;
    }
    .border {
        border: 15px solid #3B82F6;
        padding: 40px;
    }
    .content {
        text-align: center;
    }
    h1 {
        font-size: 48px;
        color: #1E40AF;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .subtitle {
        font-size: 20px;
        color: #666;
        margin: 10px 0;
    }
    .student-name {
        font-size: 42px;
        color: #111;
        margin: 30px 0;
        font-style: italic;
    }
    .course-title {
        font-size: 32px;
        color: #3B82F6;
        margin: 20px 0;
    }
    .course-info {
        font-size: 18px;
        color: #666;
        margin: 20px 0;
    }
    .details {
        display: flex;
        justify-content: space-around;
        margin: 40px 0;
        padding: 20px 0;
        border-top: 2px solid #e0e0e0;
        border-bottom: 2px solid #e0e0e0;
    }
    .details > div {
        text-align: center;
    }
    .details p {
        font-size: 16px;
        color: #666;
    }
    .details .value {
        font-size: 20px;
        color: #111;
        font-weight: bold;
        margin-top: 10px;
    }
    .verification {
        font-size: 12px;
        color: #999;
        margin-top: 30px;
        line-height: 1.6;
    }
    """

    template, created = CertificateTemplate.objects.get_or_create(
        name='Default Template',
        defaults={
            'description': 'Default certificate template',
            'html_template': default_html,
            'css_styles': default_css,
            'is_default': True
        }
    )

    return template
