# Student Enrollment Testing Guide

## Test Coverage

This test suite provides comprehensive integration testing for the student enrollment system in the Educto platform.

### StudentRegistrationTest (4 tests)
Tests for user registration functionality:
- `test_registration_page_loads` - Verifies the registration page is accessible
- `test_successful_registration` - Tests successful user account creation and redirect
- `test_registration_auto_login` - Verifies users are automatically logged in after registration
- `test_registration_password_mismatch` - Tests validation of mismatched passwords

### CourseEnrollmentTest (4 tests)
Tests for course enrollment functionality:
- `test_successful_enrollment` - Verifies students can enroll in courses
- `test_enrollment_requires_login` - Tests authentication requirement for enrollment
- `test_duplicate_enrollment_prevented` - Ensures students can only enroll once per course
- `test_enrollment_redirects_to_course_detail` - Verifies proper redirect after enrollment

### StudentCourseListTest (3 tests)
Tests for student course listing:
- `test_course_list_requires_login` - Tests authentication requirement
- `test_course_list_shows_only_enrolled_courses` - Verifies students only see their courses
- `test_course_list_uses_select_related` - Tests query optimization

### StudentCourseDetailTest (5 tests)
Tests for course detail view:
- `test_course_detail_requires_enrollment` - Verifies enrollment requirement for access
- `test_course_detail_shows_modules` - Tests module display
- `test_course_detail_displays_first_module_by_default` - Tests default module selection
- `test_course_detail_with_specific_module` - Tests specific module selection
- `test_course_detail_prefetches_contents` - Tests query optimization

### CourseEnrollFormTest (3 tests)
Tests for enrollment form validation:
- `test_form_valid_with_course` - Tests valid form submission
- `test_form_invalid_without_course` - Tests required field validation
- `test_form_invalid_with_nonexistent_course` - Tests invalid course ID handling

## Total Test Count: 19 Integration Tests

## Running Tests

### Run all student tests
```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio/config_educa
python manage.py test students
```

### Run specific test class
```bash
python manage.py test students.tests.CourseEnrollmentTest
```

### Run specific test method
```bash
python manage.py test students.tests.CourseEnrollmentTest.test_successful_enrollment
```

### Run with verbose output
```bash
python manage.py test students --verbosity=2
```

### Run with test coverage
```bash
# Install coverage if not already installed
pip install coverage

# Run tests with coverage
coverage run --source='students' manage.py test students

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
# Open htmlcov/index.html in browser
```

## Test Database

All tests use Django's test database with automatic:
- Database creation before tests
- Transactions for each test
- Automatic rollback after each test
- Database cleanup after test suite

No manual database setup required!

## What These Tests Cover

### Authentication & Authorization
- User registration flow
- Auto-login after registration
- Login requirements for protected views
- Enrollment-based access control

### Enrollment Flow
- Course enrollment process
- Duplicate enrollment prevention
- Enrollment redirects
- Student-course relationships

### Data Display
- Course list filtering (enrolled courses only)
- Module display in course detail
- Default and specific module selection

### Query Optimization
- `select_related` for foreign keys (owner, subject)
- `prefetch_related` for reverse foreign keys (modules, contents)
- Prevention of N+1 query problems

### Form Validation
- Required fields
- Valid data acceptance
- Invalid data rejection
- Foreign key validation

## Test Fixtures

Tests use `setUpTestData()` for efficient test data creation:
- Users (students, instructors)
- Subjects
- Courses
- Modules

Data is created once per test class and reused across test methods.

## Expected Test Output

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...................
----------------------------------------------------------------------
Ran 19 tests in X.XXXs

OK
Destroying test database for alias 'default'...
```

## Troubleshooting

### Redis Connection Errors
The views use Redis for caching last accessed modules. Tests should work without Redis running as Django test runner isolates database and cache backends. If Redis errors occur, check your test settings.

### Query Count Assertions
Query count tests (`assertNumQueries`) may need adjustment if:
- Django middleware changes
- Additional select_related/prefetch_related is added
- Django ORM optimization changes

### Template Errors
If template-related tests fail:
- Verify template files exist
- Check template syntax
- Ensure template directories are configured

## Best Practices Demonstrated

1. **Test Isolation**: Each test is independent
2. **Descriptive Names**: Test names clearly describe what is tested
3. **AAA Pattern**: Arrange, Act, Assert structure
4. **Edge Cases**: Tests cover success and failure scenarios
5. **Query Optimization**: Tests verify efficient database queries
6. **Security**: Tests verify authentication and authorization

## Future Test Additions

Consider adding tests for:
- Redis-based module progress tracking
- Cache invalidation
- Concurrent enrollment scenarios
- Module content display
- Course completion tracking
- Student progress analytics

## Notes

- Tests use Django's test client for integration testing
- All tests use the Django test database (not production)
- Tests verify both happy path and error conditions
- Query optimization tests ensure scalability
