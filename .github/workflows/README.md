# CI/CD Pipeline

This repository contains two GitHub Actions workflows:

1. **CI Pipeline** (`ci.yml`): Runs automated tests on every push to the main branch and on pull requests
2. **Deploy to Google Cloud Run** (`deploy.yml`): Manually triggered deployment to Google Cloud Run

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

---

# Deployment Workflow

The deployment workflow (`deploy.yml`) allows manual deployment to Google Cloud Run.

## How to Deploy

1. Go to your GitHub repository
2. Navigate to **Actions** tab
3. Select **"Deploy to Google Cloud Run"** workflow
4. Click **"Run workflow"**
5. Choose environment (production/staging)
6. Optionally specify a Docker image tag (defaults to commit SHA)

## Required Secrets for Deployment

Add these secrets to your GitHub repository (Settings > Secrets and variables > Actions):

### GCP_SA_KEY
Google Cloud service account key in JSON format. To create:

1. Go to Google Cloud Console > IAM & Admin > Service Accounts
2. Create a new service account or use existing one
3. Add these roles:
   - Cloud Run Admin
   - Container Registry Service Agent
   - Cloud Build Service Account
4. Create a JSON key and add the entire JSON content as `GCP_SA_KEY`

### GCP_PROJECT_ID
Your Google Cloud project ID (e.g., `my-project-12345`)

### GCP_REGION
Google Cloud region for deployment (e.g., `europe-west1`, `us-central1`)

### DATABASE_URL
Your production Neon PostgreSQL database connection string

### FLASK_SECRET_KEY
Random secret key for Flask sessions. Generate with:
```bash
openssl rand -hex 32
```

### OPENROUTER_API_KEY
Your OpenRouter API key for AI functionality

## Deployment Configuration

The deployment uses these settings:
- **Memory**: 1Gi
- **CPU**: 1
- **Max instances**: 10
- **Timeout**: 1200 seconds (20 minutes for AI processing)
- **Region**: Configurable via `GCP_REGION` secret
