from django.test import TestCase
from .models import Course, User, Subject, Module
from django.utils import timezone
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


from django.test import override_settings


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class CatalogHtmxTests(TestCase):
    """M3: Foundry catalog — HTMX filter + search + partial response."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="instructor", password="pw12345!")
        cls.math = Subject.objects.create(title="Mathematics", slug="m3-math")
        cls.eng = Subject.objects.create(title="English Lit", slug="m3-eng")
        cls.course_a = Course.objects.create(
            owner=cls.owner, subject=cls.math, title="Linear Algebra",
            slug="m3-linear-algebra", overview="Vectors and matrices",
        )
        cls.course_b = Course.objects.create(
            owner=cls.owner, subject=cls.eng, title="Modern Poetry",
            slug="m3-modern-poetry", overview="20th century verse",
        )

    def test_catalog_lists_all_courses(self):
        response = self.client.get(reverse("course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Linear Algebra")
        self.assertContains(response, "Modern Poetry")

    def test_catalog_filters_by_subject_query_param(self):
        response = self.client.get(reverse("course_list") + f"?subject={self.math.slug}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Linear Algebra")
        self.assertNotContains(response, "Modern Poetry")

    def test_catalog_filters_by_search_query(self):
        response = self.client.get(reverse("course_list") + "?q=poetry")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modern Poetry")
        self.assertNotContains(response, "Linear Algebra")

    def test_catalog_htmx_request_returns_partial(self):
        response = self.client.get(
            reverse("course_list") + "?q=poetry",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shared/partials/_catalog_results.html")
        # partial should NOT include the topbar/sidebar (full base)
        self.assertNotContains(response, "<header")
        self.assertContains(response, "Modern Poetry")


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    USE_FOUNDRY_UI=True,
)
class CourseDetailFoundryTests(TestCase):
    """M3: Course detail renders Foundry metadata panel + curriculum table."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="instr2", password="pw12345!")
        cls.subject = Subject.objects.create(title="Programming", slug="m3-programming")
        cls.course = Course.objects.create(
            owner=cls.owner, subject=cls.subject,
            title="Python Advanced", slug="m3-python-advanced",
            overview="Decorators, async, performance.",
        )
        cls.m1 = Module.objects.create(course=cls.course, title="Functions", description="Closures and scope")
        cls.m2 = Module.objects.create(course=cls.course, title="Decorators", description="Wrapping behavior")

    def test_detail_page_renders_curriculum(self):
        response = self.client.get(reverse("course_detail", args=[self.course.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Advanced")
        self.assertContains(response, "Functions")
        self.assertContains(response, "Decorators")

    def test_detail_page_shows_enroll_panel_for_anonymous(self):
        response = self.client.get(reverse("course_detail", args=[self.course.slug]))
        self.assertContains(response, "REGISTER TO ENROLL")

    def test_detail_page_shows_enroll_form_for_authenticated(self):
        self.client.login(username="instr2", password="pw12345!")
        response = self.client.get(reverse("course_detail", args=[self.course.slug]))
        self.assertContains(response, "ENROLL")

    def test_detail_metadata_shows_module_count(self):
        response = self.client.get(reverse("course_detail", args=[self.course.slug]))
        self.assertContains(response, "MODULES")
        # 2 modules created
        self.assertContains(response, "02")
