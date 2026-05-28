# Generated manually for certificates app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0004_course_students'),
    ]

    operations = [
        migrations.CreateModel(
            name='CertificateTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('html_template', models.TextField(help_text='HTML template with placeholders')),
                ('css_styles', models.TextField(blank=True, help_text='Custom CSS for certificate')),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Certificate Template',
                'verbose_name_plural': 'Certificate Templates',
                'ordering': ['-is_default', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Certificate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('certificate_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('issued_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completion_date', models.DateField(auto_now_add=True)),
                ('grade', models.CharField(blank=True, help_text='e.g., A, B+, Pass', max_length=10)),
                ('verification_code', models.CharField(editable=False, max_length=50, unique=True)),
                ('is_valid', models.BooleanField(default=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_reason', models.TextField(blank=True)),
                ('download_count', models.IntegerField(default=0)),
                ('last_downloaded', models.DateTimeField(blank=True, null=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to='courses.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Certificate',
                'verbose_name_plural': 'Certificates',
                'ordering': ['-issued_at'],
                'unique_together': {('user', 'course')},
            },
        ),
        migrations.AddIndex(
            model_name='certificate',
            index=models.Index(fields=['user', '-issued_at'], name='certificate_user_id_9f8a6d_idx'),
        ),
        migrations.AddIndex(
            model_name='certificate',
            index=models.Index(fields=['certificate_id'], name='certificate_certifi_7e3b8c_idx'),
        ),
        migrations.AddIndex(
            model_name='certificate',
            index=models.Index(fields=['verification_code'], name='certificate_verific_8a7c9d_idx'),
        ),
    ]
