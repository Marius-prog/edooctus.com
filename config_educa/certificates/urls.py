from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    path('request/<int:course_id>/', views.request_certificate, name='request_certificate'),
    path('view/<uuid:certificate_id>/', views.view_certificate, name='view_certificate'),
    path('download/<uuid:certificate_id>/', views.download_certificate, name='download_certificate'),
    path('verify/<str:verification_code>/', views.verify_certificate, name='verify_certificate'),
    path('my/', views.my_certificates, name='my_certificates'),
]
