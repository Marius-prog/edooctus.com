# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Educto** (educto.io) - Production Django 5.1.3 online education platform with course management, student enrollment, and real-time WebSocket chat. Deployed via Docker Compose with PostgreSQL, Redis, Nginx, and separate WSGI (uWSGI) and ASGI (Daphne) servers.

## Commands

### Development (Local with Virtual Environment)

All Django commands run from `config_educa/` directory:

```bash
# Activate virtual environment
source config_educa/venv/bin/activate

# Install/update dependencies
./scripts/update_dependencies.sh

# Database operations
cd config_educa
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Run development server (requires Redis running separately)
python manage.py runserver

# Run tests
python manage.py test                    # All tests
python manage.py test courses           # App-specific tests
python manage.py test courses.tests.CourseModelTest  # Specific test class

# Django shell
python manage.py shell
```

### Production (Docker)

```bash
# Automated deployment (recommended)
./scripts/deploy_production.sh

# Manual deployment
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker-compose exec web python config_educa/manage.py migrate
docker-compose exec web python config_educa/manage.py collectstatic --noinput

# Database operations
docker-compose exec web python config_educa/manage.py makemigrations
docker-compose exec web python config_educa/manage.py migrate
docker-compose exec web python config_educa/manage.py shell

# Monitoring
docker-compose ps                        # Service status
docker-compose logs -f                   # All logs
docker-compose logs -f web               # Specific service
docker stats                             # Resource usage

# Database backup/restore
./scripts/backup_database.sh
gunzip -c ./backups/[file].sql.gz | docker-compose exec -T db psql -U postgres postgres
```

## Architecture

### Multi-Container Production Setup

**5 Docker Services**:
1. **db** (PostgreSQL 14.5) - Primary database, persistent to `./data/db`
2. **cache** (Redis 7.0.4) - Django cache + Channels layer for WebSocket, persistent to `./data/cache`
3. **web** (Django + uWSGI) - HTTP request handler, waits for db via `wait-for-it.sh`
4. **daphne** (ASGI server) - WebSocket handler for chat, connects via Unix socket
5. **nginx** (1.23.1) - Reverse proxy, SSL termination, static/media files, routes `/ws/` to Daphne

**Request Flow**:
- HTTP: Client → Nginx → uWSGI (Unix socket) → Django WSGI
- WebSocket: Client → Nginx → Daphne (Unix socket) → Django ASGI → Redis
- Static/Media: Client → Nginx (direct serve from `/code/static/`, `/code/media/`)

### Django Applications

**courses** - Content management with generic relations
- `Subject`, `Course`, `Module`, `Content` models
- Generic FK to `ItemBase` subclasses: `Text`, `Video`, `Image`, `File`
- Ordering via custom `OrderField`
- **Optimization**: Uses `select_related('owner', 'subject')` and `prefetch_related('modules')` in views
- **Indexes**: Added on `slug`, `-created`, `owner+-created`, `subject+-created`

**students** - Enrollment and progress tracking
- Uses Django's built-in `User` model
- M2M relationship: `Course.students`
- Redis tracking: Last accessed module per student per course
- **Optimization**: `select_related('owner', 'subject').prefetch_related('modules')` in list views

**chat** - Real-time messaging
- `Message` model with FK to `Course` and `User`
- `ChatConsumer` (AsyncWebsocketConsumer) handles WebSocket connections
- **Security**: Authentication check in `connect()` - rejects unauthenticated users
- **Bug Fix**: Uses `Course.objects.aget(id=int(self.id))` then passes FK to `Message.objects.acreate()`
- **Indexes**: Added on `course+-sent_on`, `user+-sent_on`
- Room groups: `chat_{course_id}`

### Settings Structure

- `base.py` - Shared settings, now uses `os.environ.get('DJANGO_SECRET_KEY')` (NOT hardcoded)
- `local.py` - Development (SQLite, DEBUG=True, local Redis at 127.0.0.1:6379)
- `prod.py` - Production (PostgreSQL, DEBUG=False, Redis at cache:6379, security headers)

**Environment Variables Required**:
- `DJANGO_SECRET_KEY` - **MUST be set in .env file or environment**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - For production database

### Query Optimization Strategy

**All views use select_related/prefetch_related to prevent N+1 queries**:

Example pattern in `courses/views.py`:
```python
Course.objects.select_related('owner', 'subject').prefetch_related('modules__contents')
```

**Cache Strategy** (CourseListView):
- Subjects cached as `'all_subjects'`
- Courses cached as `'all_courses'` or `'subject_{id}_courses'`
- Redis backend via `django.core.cache.backends.redis.RedisCache`

## Key Files & Locations

```
/
├── config_educa/               # Django project root (run commands from here)
│   ├── manage.py              # Django management script
│   ├── config_educa/
│   │   ├── settings/          # Modular settings (base, local, prod)
│   │   ├── asgi.py           # ASGI config for WebSocket
│   │   └── urls.py           # Root URL configuration
│   ├── courses/              # Course management app
│   ├── students/             # Enrollment app
│   ├── chat/                 # WebSocket chat app
│   │   ├── consumers.py      # ChatConsumer with auth check
│   │   └── models.py         # Message model
│   ├── static/               # Collected static files (after collectstatic)
│   └── media/                # User uploads
├── config/
│   ├── nginx/                # Nginx reverse proxy config
│   │   └── default.conf.template  # With security headers + rate limiting
│   ├── uwsgi/                # uWSGI application server config
│   └── certbot/              # SSL certificates
├── scripts/                  # Deployment automation
│   ├── update_dependencies.sh
│   ├── run_migrations.sh
│   ├── deploy_production.sh
│   └── backup_database.sh
├── data/                     # Persistent data (gitignored)
│   ├── db/                   # PostgreSQL data
│   └── cache/                # Redis data
├── backups/                  # Database backups (auto-created by backup script)
├── requirements.txt          # Python dependencies (Django 5.1.3, 52 packages)
├── docker-compose.yml        # Multi-container orchestration with resource limits
├── Dockerfile                # Application container definition
├── .env.example              # Environment variable template
└── wait-for-it.sh           # Database readiness check script
```

## Important Implementation Details

### WebSocket Chat Security (CRITICAL)

**Authentication is enforced** in `chat/consumers.py`:
```python
async def connect(self):
    self.user = self.scope['user']
    if not self.user.is_authenticated:
        await self.close()
        return
    # ... rest of connection logic
```

**Message persistence** uses proper FK:
```python
from courses.models import Course
course = await Course.objects.aget(id=int(self.id))
await Message.objects.acreate(user=self.user, course=course, content=message)
```

### Security Configurations

**Nginx Security Headers** (`config/nginx/default.conf.template`):
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Content-Security-Policy: (comprehensive policy)
- **Rate Limiting**: 10 req/s per IP (burst: 20)

**Django Production Settings** (`settings/prod.py`):
- `DEBUG = False`
- `ALLOWED_HOSTS = ['educto.io', 'www.educto.io']` - **NO wildcards**
- SSL redirects, HSTS (31536000s), secure cookies
- Admin URL obfuscated to `/(K+J+u.dt8/`

**Docker Resource Limits** (prevents OOM crashes):
- PostgreSQL: 1 CPU, 1GB RAM
- Redis: 0.5 CPU, 512MB RAM
- Django/uWSGI: 1 CPU, 1GB RAM
- Daphne: 0.5 CPU, 512MB RAM
- All services have health checks (30s interval)

### Database Indexes

**Performance-critical indexes added** (require migrations):

`Course` model:
- `Index(fields=['slug'])` - Course lookups
- `Index(fields=['-created'])` - Latest courses
- `Index(fields=['owner', '-created'])` - User's courses
- `Index(fields=['subject', '-created'])` - Subject filtering

`Message` model:
- `Index(fields=['course', '-sent_on'])` - Chat history
- `Index(fields=['user', '-sent_on'])` - User messages

### Testing

**Test Structure**:
- `courses/tests.py` - Comprehensive model and URL tests
- Tests include: Model validation, M2M relationships, ordering, URL resolution
- **New tests for optimizations**: `test_course_indexes_exist()`, `test_select_related_optimization()`
- `chat/tests.py`, `students/tests.py` - Framework exists, needs implementation

**Run specific tests**:
```bash
python manage.py test courses.tests.CourseModelTest.test_course_indexes_exist
```

## Development Workflow

### Starting New Work

1. **Activate environment**: `source config_educa/venv/bin/activate`
2. **Update dependencies** (if needed): `./scripts/update_dependencies.sh`
3. **Start Redis**: `redis-server` (separate terminal)
4. **Run migrations**: `cd config_educa && python manage.py migrate`
5. **Start dev server**: `python manage.py runserver`
6. **Access**:
   - App: http://127.0.0.1:8000
   - Admin: http://127.0.0.1:8000/(K+J+u.dt8/
   - Debug Toolbar: http://127.0.0.1:8000/__debug__/

### Adding New Models

1. Define model in `app/models.py`
2. **Add indexes** for frequently queried fields in `Meta.indexes`
3. `python manage.py makemigrations`
4. Review migration file
5. `python manage.py migrate`
6. **Update views** to use `select_related()` / `prefetch_related()`
7. **Write tests** in `app/tests.py`

### Deploying Changes

**Local Testing First**:
```bash
./scripts/run_migrations.sh
cd config_educa && python manage.py test
```

**Production Deployment**:
```bash
# Ensure .env exists with DJANGO_SECRET_KEY
./scripts/deploy_production.sh
# OR manual:
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Verify deployment**:
```bash
docker-compose ps                     # All services "Up" and "healthy"
docker-compose logs -f web            # Check for errors
curl -I https://educto.io             # Verify security headers
```

## Troubleshooting

### Common Issues

**"django not found"**: Virtual environment not activated
```bash
source config_educa/venv/bin/activate
```

**"DJANGO_SECRET_KEY not set"**: Missing environment variable
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"  # Generate key
echo "DJANGO_SECRET_KEY=your-key-here" > .env
```

**Chat not working**: Redis not running or authentication failed
```bash
# Local: redis-server
# Docker: docker-compose logs -f cache
# Check ChatConsumer authentication in chat/consumers.py
```

**Slow queries**: Missing indexes or select_related
```bash
# Enable Debug Toolbar to see query counts
# Add indexes to models
# Use select_related() in views
```

**Docker service unhealthy**: Check logs and health check
```bash
docker-compose ps                      # See which service is unhealthy
docker-compose logs -f [service]       # View service logs
docker-compose restart [service]       # Restart specific service
```

## Recent Improvements (October 2025)

See `IMPROVEMENTS_COMPLETE.md` for full details:

- ✅ **Security**: SECRET_KEY moved to env var, ALLOWED_HOSTS fixed, WebSocket auth added, 52 dependencies updated (Django 5.1.3, Pillow 11.0, urllib3 2.2.3)
- ✅ **Performance**: 6 database indexes added, 9 views optimized with select_related/prefetch_related (5-20x query reduction)
- ✅ **Infrastructure**: Docker resource limits + health checks, Nginx security headers + rate limiting (10 req/s)
- ✅ **Automation**: 4 deployment scripts created (update, migrate, deploy, backup)
- ✅ **Testing**: Enhanced test coverage for optimizations

**Deployment requires**:
1. Set `DJANGO_SECRET_KEY` in `.env` file
2. Run `./scripts/run_migrations.sh` to create indexes
3. Update dependencies with `./scripts/update_dependencies.sh`
