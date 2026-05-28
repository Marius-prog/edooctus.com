#!/bin/bash
# Production Deployment Script
# Deploys the Educto platform to production using Docker Compose

set -e  # Exit on error

echo "🚀 Deploying Educto to Production..."
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo ""
    echo "Please create a .env file with your secret key:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your DJANGO_SECRET_KEY"
    echo ""
    exit 1
fi

# Source environment variables
set -a
source .env
set +a

# Verify SECRET_KEY is set
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "❌ ERROR: DJANGO_SECRET_KEY not set in .env file!"
    echo ""
    echo "Generate a new key with:"
    echo "  python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    echo ""
    exit 1
fi

echo "✅ Environment variables loaded"
echo ""

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

echo ""
echo "🔨 Building Docker images..."
docker-compose build --no-cache

echo ""
echo "⬆️  Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 10

echo ""
echo "🗄️  Running database migrations..."
docker-compose exec -T web python config_educa/manage.py migrate

echo ""
echo "📦 Collecting static files..."
docker-compose exec -T web python config_educa/manage.py collectstatic --noinput

echo ""
echo "🔍 Checking service health..."
docker-compose ps

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "📝 View logs with:"
echo "  docker-compose logs -f"
echo ""
echo "🌐 Your site should be available at:"
echo "  https://educto.io"
echo "  https://www.educto.io"
