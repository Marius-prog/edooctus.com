#!/bin/bash

# Chat Test Runner Script
# This script runs the comprehensive chat test suite

echo "========================================"
echo "Chat Application Test Suite"
echo "========================================"
echo ""

# Check if Redis is running
echo "Checking Redis server..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "ERROR: Redis is not running!"
    echo "Please start Redis with: redis-server --daemonize yes"
    exit 1
fi
echo "✓ Redis is running"
echo ""

# Activate virtual environment (adjust path if needed)
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
    echo "✓ Virtual environment activated"
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "WARNING: No virtual environment found"
fi
echo ""

# Run tests
echo "Running chat tests..."
echo "========================================"
python manage.py test chat --verbosity=2

# Capture exit code
EXIT_CODE=$?

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Some tests failed (exit code: $EXIT_CODE)"
fi
echo "========================================"

exit $EXIT_CODE
