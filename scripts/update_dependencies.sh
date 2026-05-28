#!/bin/bash
# Update Dependencies Script
# This script updates all Python dependencies to the latest versions

set -e  # Exit on error

echo "🔄 Updating Dependencies for Educto Platform..."
echo ""

# Check if virtual environment exists
if [ ! -d "config_educa/venv" ]; then
    echo "❌ Virtual environment not found at config_educa/venv"
    echo "Creating virtual environment..."
    python3 -m venv config_educa/venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source config_educa/venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install updated dependencies
echo "📦 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Dependencies updated successfully!"
echo ""
echo "Next steps:"
echo "  1. Run migrations: ./scripts/run_migrations.sh"
echo "  2. Run tests: cd config_educa && python manage.py test"
echo "  3. Start dev server: cd config_educa && python manage.py runserver"
