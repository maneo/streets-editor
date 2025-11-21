# CI/CD Pipeline

This workflow runs automated tests on every push to the main branch and on pull requests.

## Jobs

### Unit Tests
- Runs pytest on all unit tests (excluding e2e tests)
- Uses PostgreSQL service for database testing
- Includes linting with Ruff

### E2E Tests
- Runs Playwright end-to-end tests
- Requires the Flask application to be running
- Creates test database and test user before running tests
- Uploads test artifacts (videos, screenshots) on failure

## Required Secrets

Add the following secrets to your GitHub repository:

### OPENROUTER_API_KEY
Your OpenRouter API key for AI functionality. This is optional for tests but recommended to have a test key.

To add secrets:
1. Go to your repository on GitHub
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Add `OPENROUTER_API_KEY` with your API key

## Local Testing

To test the workflow locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. Run unit tests:
   ```bash
   pytest tests/ -m "not e2e"
   ```

3. Run E2E tests:
   ```bash
   ./run_e2e_tests.sh
   ```

## Environment Variables

The workflow uses these environment variables:
- `DATABASE_URL`: PostgreSQL connection string for tests
- `SECRET_KEY`: Flask secret key for sessions
- `OPENROUTER_API_KEY`: API key for OpenRouter (from secrets)
- `FLASK_ENV`: Set to 'testing' for test configuration
- `TEST_BASE_URL`: Base URL for E2E tests (http://localhost:5000)
