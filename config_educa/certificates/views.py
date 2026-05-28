from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from courses.models import Course
from .models import Certificate
from .utils import check_course_completion, generate_certificate_html


@login_required
def request_certificate(request, course_id):
    """Request certificate for completed course"""
    course = get_object_or_404(Course, id=course_id)

    # Check if user is enrolled
    if not course.students.filter(id=request.user.id).exists():
        messages.error(request, 'You must be enrolled in this course.')
        return redirect('course_detail', slug=course.slug)

    # Check if course is completed
    if not check_course_completion(request.user, course):
        messages.error(request, 'You must complete all modules to receive a certificate.')
        return redirect('student_course_detail', pk=course.id)

    # Get or create certificate
    certificate, created = Certificate.objects.get_or_create(
        user=request.user,
        course=course
    )

    if created:
        messages.success(request, 'Congratulations! Your certificate has been generated.')
    else:
        messages.info(request, 'You already have a certificate for this course.')

    return redirect('certificates:view_certificate', certificate_id=certificate.certificate_id)


@login_required
def view_certificate(request, certificate_id):
    """View certificate"""
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)

    # Only allow owner to view
    if certificate.user != request.user:
        messages.error(request, 'You do not have permission to view this certificate.')
        return redirect('student_course_list')

    if not certificate.is_valid:
        messages.warning(request, 'This certificate has been revoked.')

    html = generate_certificate_html(certificate)
    return HttpResponse(html)


@login_required
def download_certificate(request, certificate_id):
    """Download certificate as PDF"""
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)

    # Only allow owner to download
    if certificate.user != request.user:
        messages.error(request, 'You do not have permission to download this certificate.')
        return redirect('student_course_list')

    # Track download
    certificate.track_download()

    # For now, return HTML (PDF generation requires additional library)
    html = generate_certificate_html(certificate)
    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="certificate_{certificate.certificate_id}.html"'

    messages.info(request, 'For PDF download, use your browser\'s Print > Save as PDF feature.')
    return response


def verify_certificate(request, verification_code):
    """Public certificate verification page"""
    try:
        certificate = Certificate.objects.get(verification_code=verification_code)
        is_valid = certificate.is_valid
    except Certificate.DoesNotExist:
        certificate = None
        is_valid = False

    return render(request, 'certificates/verify.html', {
        'certificate': certificate,
        'is_valid': is_valid,
        'verification_code': verification_code
    })


@login_required
def my_certificates(request):
    """List all user's certificates"""
    certificates = Certificate.objects.filter(user=request.user, is_valid=True)

    return render(request, 'certificates/my_certificates.html', {
        'certificates': certificates
    })
