#!/bin/bash

# Script to run end-to-end tests
# Make sure to activate your virtual environment first

echo "🚀 Starting Flask application..."
python run.py &
FLASK_PID=$!

echo "⏳ Waiting for Flask to start..."
sleep 3

echo "🧪 Running E2E tests..."
pytest tests/e2e/ -v --tb=short

echo "🛑 Stopping Flask application..."
kill $FLASK_PID

echo "✅ E2E tests completed!"
