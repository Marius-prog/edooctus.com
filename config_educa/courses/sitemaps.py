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
