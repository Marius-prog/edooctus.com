# Django Education Platform (config_educa)

## Project Overview

This is a Django-based online education platform called "Educto" that provides course management, student enrollment, and real-time chat functionality. The platform is deployed at educto.io and www.educto.io.

## Architecture

### Core Applications

1. **courses** - Course and content management system
   - Course creation and management
   - Module and content organization
   - Subject categorization
   - Support for multiple content types (Text, Video, Image, File)
   - Uses generic foreign keys for flexible content relationships

2. **students** - Student enrollment and course access
   - Student registration and authentication
   - Course enrollment functionality
   - Student course dashboard and detail views

3. **chat** - Real-time chat functionality
   - WebSocket-based chat rooms per course
   - Uses Django Channels for WebSocket support
   - Redis-backed channel layers for message distribution

### Technology Stack

- **Framework**: Django 4.2
- **WebSocket Support**: Django Channels
- **Database**: 
  - Development: SQLite3
  - Production: PostgreSQL
- **Cache/Message Broker**: Redis
- **API**: Django REST Framework
- **Video Embedding**: django-embed-video
- **Development Tools**: 
  - django-debug-toolbar
  - django-extensions
  - redisboard (Redis monitoring)

### Database Models

#### Courses App
- `Subject`: Course categories
- `Course`: Main course entity with owner, students (M2M), and metadata
- `Module`: Course modules with ordering
- `Content`: Generic content container using ContentType framework
- `ItemBase`: Abstract base for content types (Text, Video, Image, File)

#### Students App
- Uses Django's built-in User model
- Course enrollment through M2M relationship

#### Chat App
- No persistent models (real-time messaging only)

## Settings Configuration

The project uses a modular settings structure:

- `base.py` - Common settings for all environments
- `local.py` - Development environment (SQLite, DEBUG=True)
- `prod.py` - Production environment (PostgreSQL, security settings)

### Key Configuration

- **Default Settings Module**: `config_educa.settings` (points to base.py)
- **ASGI Application**: Configured for WebSocket support
- **Redis Configuration**: Used for caching and WebSocket channel layers
- **REST Framework**: Basic permissions setup
- **Media Files**: Uploaded to `/media/` directory

## Running the Application

### Development Setup

1. **Install Dependencies** (Note: No requirements.txt found - dependencies need to be identified)
   ```bash
   # Core dependencies likely include:
   pip install django==4.2
   pip install channels
   pip install channels-redis
   pip install django-rest-framework
   pip install django-embed-video
   pip install django-debug-toolbar
   pip install django-extensions
   pip install redis
   ```

2. **Database Setup**
   ```bash
   python manage.py migrate
   ```

3. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

4. **Load Initial Data** (if needed)
   ```bash
   python manage.py loaddata courses/fixtures/subjects.json
   ```

5. **Start Redis Server** (required for chat functionality)
   ```bash
   redis-server
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

### Production Deployment

- Uses PostgreSQL database
- Requires environment variables: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Redis configuration: `redis://cache:6379`
- SSL certificates located in `/ssl/` directory
- Security headers enabled (HSTS, secure cookies, SSL redirect)

## API Endpoints

The platform includes REST API endpoints under `/api/`:

- Course management APIs
- Student enrollment endpoints
- Example enrollment script available in `api_examples/enroll_all.py`

## WebSocket Chat System

### Architecture
- **ASGI Configuration**: `/config_educa/asgi.py`
- **WebSocket Routing**: `/chat/routing.py`
- **Consumer**: `ChatConsumer` handles real-time messaging
- **URL Pattern**: `ws/chat/room/{course_id}/`

### Features
- Course-specific chat rooms
- User authentication required
- Real-time message broadcasting
- Timestamp support

## URL Structure

- `/` - Course list (homepage)
- `/course/` - Course management URLs
- `/students/` - Student-specific URLs
- `/chat/` - Chat functionality
- `/api/` - REST API endpoints
- `/accounts/login/` - Authentication
- `/(K+J+u.dt8/` - Admin interface (obfuscated URL)

## Testing

- Test files exist in each app but appear to be empty
- Framework in place for unit testing

## Development Commands

### Common Django Commands
```bash
# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Django shell
python manage.py shell

# Run tests
python manage.py test
```

### Debug and Development Tools
- Debug toolbar available at `/__debug__/`
- Redis monitoring through redisboard
- Django extensions for enhanced shell and management commands

## Security Notes

- Secret key is exposed in base.py (should be moved to environment variables)
- Production settings include comprehensive security headers
- CSRF and session security configured for production
- Admin URL is obfuscated for security

## File Structure

- **Static files**: Collected in `/static/`
- **Media uploads**: Stored in `/media/` with subfolders for different content types
- **Templates**: App-specific templates in each app's `/templates/` directory
- **SSL certificates**: Located in `/ssl/` directory

## Missing Components

- No requirements.txt file (dependencies must be determined from imports)
- No Docker configuration
- Test files are empty
- No comprehensive documentation beyond this file

This platform appears to be a fully functional online education system with modern features including real-time chat, REST APIs, and a clean Django architecture.