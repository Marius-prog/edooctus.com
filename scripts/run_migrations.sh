#!/bin/bash
# Run Database Migrations Script
# Creates and applies database migrations for the Educto platform

set -e  # Exit on error

echo "🗄️  Running Database Migrations..."
echo ""

# Activate virtual environment
source config_educa/venv/bin/activate

# Navigate to Django project
cd config_educa

# Create migrations
echo "📝 Creating new migrations..."
python manage.py makemigrations

echo ""
echo "🔍 Checking migration plan..."
python manage.py showmigrations

echo ""
echo "⚡ Applying migrations..."
python manage.py migrate

echo ""
echo "✅ Migrations completed successfully!"
echo ""
echo "📊 Current database state:"
python manage.py showmigrations

cd ..
