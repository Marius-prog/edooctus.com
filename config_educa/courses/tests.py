from django.test import TestCase
from .models import Course, User, Subject, Module, Text, File, Image, Video
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse, resolve
from . import views


class SubjectModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        Subject.objects.create(title='Mathematics', slug='mathematics')
        Subject.objects.create(title='English Literature', slug='english-literature')

    def test_title_label(self):
        subject = Subject.objects.get(id=1)
        field_label = subject._meta.get_field('title').verbose_name
        self.assertEqual(field_label, 'title')

    def test_slug_label(self):
        subject = Subject.objects.get(id=1)
        field_label = subject._meta.get_field('slug').verbose_name
        self.assertEqual(field_label, 'slug')

    def test_title_max_length(self):
        subject = Subject.objects.get(id=1)
        max_length = subject._meta.get_field('title').max_length
        self.assertEqual(max_length, 200)

    def test_slug_max_length(self):
        subject = Subject.objects.get(id=1)
        max_length = subject._meta.get_field('slug').max_length
        self.assertEqual(max_length, 200)

    def test_object_name_is_title(self):
        subject = Subject.objects.get(id=1)
        expected_object_name = f'{subject.title}'
        self.assertEqual(expected_object_name, str(subject))

    # def test_ordering(self):
    #     subjects = Subject.objects.all()
    #     self.assertQuerysetEqual(subjects, ['<Subject: English Literature>', '<Subject: Mathematics>'])

    def test_slug_field_is_unique(self):
        subject = Subject(title='Mathematics', slug='mathematics')
        with self.assertRaises(Exception):
            subject.save()


class CourseModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Set up non-modified objects used by all test methods
        cls.subject = Subject.objects.create(title='Mathematics', slug='mathematics')
        cls.user = User.objects.create_user(username='testuser', password='12345')
        Course.objects.create(owner=cls.user,
                              subject=cls.subject,
                              title='Algebra',
                              slug='algebra',
                              overview='This is a course on algebra')

    def test_title_label(self):
        course = Course.objects.get(id=1)
        field_label = course._meta.get_field('title').verbose_name
        self.assertEqual(field_label, 'title')

    def test_slug_label(self):
        course = Course.objects.get(id=1)
        field_label = course._meta.get_field('slug').verbose_name
        self.assertEqual(field_label, 'slug')

    def test_title_max_length(self):
        course = Course.objects.get(id=1)
        max_length = course._meta.get_field('title').max_length
        self.assertEqual(max_length, 200)

    def test_slug_max_length(self):
        course = Course.objects.get(id=1)
        max_length = course._meta.get_field('slug').max_length
        self.assertEqual(max_length, 200)

    def test_object_name_is_title(self):
        course = Course.objects.get(id=1)
        expected_object_name = f'{course.title}'
        self.assertEqual(expected_object_name, str(course))

    def test_ordering(self):
        Course.objects.create(owner=self.user,
                              subject=self.subject,
                              title='Geometry',
                              slug='geometry',
                              overview='This is a course on geometry')
        Course.objects.create(owner=self.user,
                              subject=self.subject,
                              title='Calculus',
                              slug='calculus',
                              overview='This is a course on calculus')
        courses = Course.objects.all()
        self.assertEqual(courses.count(), 3)
        self.assertEqual(courses[0].title, 'Calculus')
        self.assertEqual(courses[1].title, 'Geometry')
        self.assertEqual(courses[2].title, 'Algebra')

    def test_created_date(self):
        course = Course.objects.get(id=1)
        self.assertLess(course.created, timezone.now())

    def test_students_m2m_relationship(self):
        course = Course.objects.get(id=1)
        student = User.objects.create_user(username='student', password='12345')
        course.students.add(student)
        self.assertEqual(course.students.count(), 1)
        self.assertEqual(course.students.first().username, 'student')
        self.assertEqual(student.courses_joined.count(), 1)
        self.assertEqual(student.courses_joined.first().title, 'Algebra')

    def test_course_indexes_exist(self):
        """Test that database indexes are defined in Course model Meta"""
        course_meta = Course._meta
        self.assertTrue(hasattr(course_meta, 'indexes'))
        self.assertGreater(len(course_meta.indexes), 0)
        # Check that indexes include important fields
        index_fields = [list(index.fields) for index in course_meta.indexes]
        self.assertTrue(any('slug' in fields for fields in index_fields))
        self.assertTrue(any('-created' in fields for fields in index_fields))

    def test_select_related_optimization(self):
        """Test that select_related works correctly for owner and subject"""
        course = Course.objects.select_related('owner', 'subject').get(id=1)
        # Access related objects without additional queries
        self.assertEqual(course.owner.username, 'testuser')
        self.assertEqual(course.subject.title, 'Mathematics')


class ModuleModelTest(TestCase):

    def test_module_does_not_exist(self):
        with self.assertRaises(Module.DoesNotExist):
            Module.objects.get(id=999)


class UrlsTest(TestCase):

    def test_manage_course_list_url_resolves(self):
        url = reverse('manage_course_list')
        self.assertEqual(resolve(url).func.view_class, views.ManageCourseListView)

    def test_course_create_url_resolves(self):
        url = reverse('course_create')
        self.assertEqual(resolve(url).func.view_class, views.CourseCreateView)

    def test_course_edit_url_resolves(self):
        url = reverse('course_edit', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.CourseUpdateView)

    def test_course_delete_url_resolves(self):
        url = reverse('course_delete', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.CourseDeleteView)

    def test_course_module_update_url_resolves(self):
        url = reverse('course_module_update', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.CourseModuleUpdateView)

    def test_module_content_create_url_resolves(self):
        url = reverse('module_content_create', args=[1, 'text'])
        self.assertEqual(resolve(url).func.view_class, views.ContentCreateUpdateView)

    def test_module_content_update_url_resolves(self):
        url = reverse('module_content_update', args=[1, 'text', 1])
        self.assertEqual(resolve(url).func.view_class, views.ContentCreateUpdateView)

    def test_module_content_delete_url_resolves(self):
        url = reverse('module_content_delete', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ContentDeleteView)

    def test_module_content_list_url_resolves(self):
        url = reverse('module_content_list', args=[1])
        self.assertEqual(resolve(url).func.view_class, views.ModuleContentListView)

    def test_module_order_url_resolves(self):
        url = reverse('module_order')
        self.assertEqual(resolve(url).func.view_class, views.ModuleOrderView)

    def test_content_order_url_resolves(self):
        url = reverse('content_order')
        self.assertEqual(resolve(url).func.view_class, views.ContentOrderView)

    def test_course_list_subject_url_resolves(self):
        url = reverse('course_list_subject', args=['mathematics'])
        self.assertEqual(resolve(url).func.view_class, views.CourseListView)

    def test_course_detail_url_resolves(self):
        url = reverse('course_detail', args=['mathematics-course'])
        self.assertEqual(resolve(url).func.view_class, views.CourseDetailView)
