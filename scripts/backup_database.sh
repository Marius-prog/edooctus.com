#!/bin/bash
# Database Backup Script
# Creates a timestamped backup of the PostgreSQL database

set -e  # Exit on error

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/educto_backup_${TIMESTAMP}.sql.gz"

echo "💾 Creating Database Backup..."
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if Docker container is running
if ! docker-compose ps | grep -q "db.*Up"; then
    echo "❌ ERROR: Database container is not running!"
    echo "Start it with: docker-compose up -d db"
    exit 1
fi

echo "📦 Backing up database to: ${BACKUP_FILE}"
docker-compose exec -T db pg_dump -U postgres postgres | gzip > "${BACKUP_FILE}"

# Get backup size
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)

echo ""
echo "✅ Backup completed successfully!"
echo "📁 File: ${BACKUP_FILE}"
echo "📊 Size: ${BACKUP_SIZE}"
echo ""

# List recent backups
echo "📋 Recent backups:"
ls -lh "${BACKUP_DIR}" | tail -n 5

# Cleanup old backups (keep last 7 days)
echo ""
echo "🧹 Cleaning up old backups (keeping last 7 days)..."
find "${BACKUP_DIR}" -name "educto_backup_*.sql.gz" -mtime +7 -delete

echo ""
echo "💡 To restore this backup:"
echo "  gunzip -c ${BACKUP_FILE} | docker-compose exec -T db psql -U postgres postgres"
