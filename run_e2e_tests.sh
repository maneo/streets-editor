#!/bin/bash

# Script to run end-to-end tests

# Activate virtual environment if it exists (for local development)
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "🚀 Activating virtual environment..."
    source venv/bin/activate
else
    echo "📦 Using system Python environment..."
fi

echo "🚀 Starting Flask application..."
python run.py &
FLASK_PID=$!

echo "⏳ Waiting for Flask to start..."
sleep 3

echo "🧪 Running E2E tests..."
pytest tests/e2e/ -v --tb=short
TEST_EXIT_CODE=$?

echo "🛑 Stopping Flask application..."
kill $FLASK_PID

echo "🧹 Cleaning up test database..."
python -c "
from app import create_app, db
app = create_app('testing')
with app.app_context():
    db.drop_all()
    print('Test database cleaned up successfully')
"

echo "✅ E2E tests completed!"

# Exit with the test result code
exit $TEST_EXIT_CODE
