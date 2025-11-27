# Streets Dictionary Editor

A web application for creating and editing street dictionaries from historical city maps using AI-powered extraction.

## Features

- Upload historical city map scans (JPG/PNG, up to 50 MB)
- Automatic street name extraction using Gemini 2.5 Pro via OpenRouter
- Manual verification and editing of extracted streets
- Export dictionaries in TXT or JSON format
- Simple user authentication system

## Tech Stack

### Frontend
- Jinja2 templates (Flask's built-in templating)
- Vanilla JavaScript for dynamic interactions
- Bulma CSS for styling

### Backend
- Python with Flask framework
- PostgreSQL database (Neon for production/testing, local Docker for development)
- SQLAlchemy ORM
- Flask-Login for authentication

### Deployment
- Google Cloud Run for serverless container deployment
- Docker for containerization
- Gunicorn for production WSGI server

### AI Integration
- OpenRouter.ai for accessing AI models
- Gemini 2.5 Pro for street extraction

## Setup

### Prerequisites

- Python 3.11+
- OpenRouter API key
- Neon account (for production and testing databases)
- Docker (for local development and Cloud Run deployment)
- Google Cloud CLI (`gcloud`) (for Cloud Run deployment)

### Installation

1. Clone the repository and navigate to the project directory

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Setup environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

#### Required Environment Variables

**Core Application:**
- `SECRET_KEY`: Your Flask secret key (required for all environments)
- `DATABASE_URL`: PostgreSQL connection string (required for production and e2e testing)

**AI Integration (Required for street extraction):**
- `OPENROUTER_API_KEY`: Your OpenRouter API key

#### Optional Environment Variables

**File Upload & Processing:**
- `MAX_UPLOAD_SIZE`: Maximum upload file size in bytes (default: 52428800 = 50MB)
- `UPLOAD_FOLDER`: Local upload directory path (default: "app/static/uploads")
- `BATCH_INSERT_SIZE`: Number of database records to insert in batch operations (default: 50)

**AI Model Configuration:**
- `EXTRACTION_MODEL`: AI model for street name extraction (default: "google/gemini-2.5-pro")

**Google Cloud Storage (Required if using GCS for file storage):**
- `GCP_PROJECT_ID`: Your Google Cloud Project ID
- `GCS_BUCKET_DEV`: GCS bucket name for development (default: "streets-editor-dev")
- `GCS_BUCKET_TEST`: GCS bucket name for testing (default: "streets-editor-test")
- `GCS_BUCKET_PROD`: GCS bucket name for production (default: "streets-editor-prod")
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCS service account key file (alternative to GCP_SA_KEY)
- `GCP_SA_KEY`: Path to GCS service account key file (alternative to GOOGLE_APPLICATION_CREDENTIALS)

**Deployment:**
- `FLASK_ENV`: Environment mode (development/production/testing, affects GCS bucket selection)
- `PORT`: Port for web server (default: 8080 for Cloud Run, 5000 for local development)

**Testing:**
- `DATABASE_URL_E2E`: Neon database URL for e2e testing (separate from production)
- `TEST_BASE_URL`: Base URL for e2e tests (default: "http://localhost:5000")
- `CI`: Set to any value when running in CI environment (enables test artifacts like videos)

**Environment File Strategy:**
Use a single `.env` file containing all environments. The application automatically selects the appropriate database:
- **Local development:** Uses Docker Compose PostgreSQL or SQLite fallback
- **E2E testing:** Uses `DATABASE_URL_E2E` when running `pytest tests/e2e/`
- **Production:** Uses `DATABASE_URL` for the main application


#### Database Setup

**Local Development Database**
- Use Docker Compose for local PostgreSQL:
```bash
docker-compose up -d db  # Start only PostgreSQL
```

5. Migrate databases using test-first workflow:
```bash
# Step 1: Apply migrations to e2e branch first for testing
DATABASE_URL=$DATABASE_URL_E2E flask db upgrade

# Step 2: Test your changes on e2e
DATABASE_URL_E2E=$DATABASE_URL_E2E pytest tests/e2e/

# Step 3: When testing passes, apply to production branch
DATABASE_URL=$DATABASE_URL flask db upgrade
```

6. Run the application:
```bash
# Local development with Docker
docker-compose up

# Or run directly
python run.py
```

The application will be available at `http://localhost:5000`

## Usage

1. Register a new account or login
2. Upload a historical city map with city name and decade
3. Wait for AI extraction (≤ 20 minutes for large/complex images)
4. Review and edit extracted streets
5. Export your dictionary as TXT or JSON

7. Run tests

The project includes multiple types of tests. Choose the appropriate test command based on what you want to test:

#### Unit Tests
Run unit tests that test individual components without requiring a running web server:
```bash
pytest tests/ -k "not e2e"
```

#### End-to-End Tests
Run full browser-based tests that simulate user interactions. These require the Flask application to be running:
```bash
# Please use the dedicated e2e test script (recommended)
./run_e2e_tests.sh

```

#### Specific Test Categories
```bash
# Run only API tests
pytest tests/test_api_*.py

# Run only model tests
pytest tests/test_models.py

# Run only service tests
pytest tests/test_services.py
```

### CLI Commands

#### Development and Testing

**Create a test user:**
```bash
flask create-test-user
# Default: test@example.com / password123

# Custom credentials:
flask create-test-user --email admin@test.com --password admin123
```

**List all users:**
```bash
flask list-users
```

**Clear database:**
```bash
flask clear-db
# Requires confirmation
```
## Project Structure

```
streets-editor/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # Blueprint routes
│   ├── services/        # Business logic
│   ├── static/          # CSS and JavaScript
│   └── templates/       # HTML templates
├── tests/               # Test files
├── migrations/          # Database migrations
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── setup-gcp.sh        # Google Cloud setup script
└── run.py              # Application entry point
```

## Docker Deployment

### Local Development with Docker Compose

Use Docker Compose for local development with PostgreSQL:

```bash
# Start all services (PostgreSQL + web app)
docker-compose up

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

### Production Deployment

Build and run with Docker for production:

```bash
docker build -t streets-editor .
docker run -p 5000:5000 --env-file .env streets-editor
```

The production deployment uses your Neon database configured in `DATABASE_URL`.

### Google Cloud Run Deployment

Deploy your application to Google Cloud Run for serverless container execution.

#### Prerequisites

- Google Cloud account and project
- Google Cloud CLI (`gcloud`) installed and authenticated
- Docker configured for Google Container Registry

#### Initial Setup
```bash
# Run the automated setup script
./setup-gcp.sh
```

2. **Build and Push Container:**
```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/streets-editor .
```

3. **Deploy to Cloud Run:**
```bash
gcloud run deploy streets-editor \
  --image gcr.io/$PROJECT_ID/streets-editor \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=your_neon_database_url" \
  --set-env-vars="SECRET_KEY=your_random_secret_key" \
  --set-env-vars="OPENROUTER_API_KEY=your_openrouter_key" \
  --set-env-vars="FLASK_ENV=production" \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --timeout=1200
```

#### GitHub Actions Configuration

Configure these **secrets** in your repository settings (Settings → Secrets and variables → Actions):

**Required Secrets:**
- `GCP_SA_KEY`: JSON key for your Google Cloud service account
- `DATABASE_URL`: Production Neon PostgreSQL connection string
- `DATABASE_URL_E2E`: E2E testing Neon database URL
- `FLASK_SECRET_KEY`: Random secret key (generate with `openssl rand -hex 32`)
- `OPENROUTER_API_KEY`: Your OpenRouter API key

**Repository Variables:**
- `GCP_PROJECT_ID`: Your Google Cloud Project ID
- `GCP_REGION`: Your preferred Google Cloud region (e.g., `europe-west1`)

#### CI Environment Variables

The GitHub Actions CI pipeline automatically sets these environment variables for testing:

**Unit Tests:**
- `SECRET_KEY`: test-secret-key
- `OPENROUTER_API_KEY`: From repository secrets
- `FLASK_ENV`: testing
- `GCP_PROJECT_ID`: ${{ vars.GCP_PROJECT_ID }} (required for GCS service initialization, uses mock client in testing)
- `EXTRACTION_MODEL`: google/gemini-2.5-pro

**E2E Tests:**
- `SECRET_KEY`: test-secret-key
- `OPENROUTER_API_KEY`: From repository secrets
- `FLASK_ENV`: testing
- `FLASK_APP`: run.py
- `DATABASE_URL`: From DATABASE_URL_E2E secret
- `GCP_PROJECT_ID`: ${{ vars.GCP_PROJECT_ID }} (required for GCS service initialization, uses mock client in testing)
- `EXTRACTION_MODEL`: google/gemini-2.5-pro

#### Environment Variables

Required environment variables for production:
- `DATABASE_URL`: Your Neon PostgreSQL connection string
- `SECRET_KEY`: Random secret key (generate with `openssl rand -hex 32`)
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `FLASK_ENV`: Set to `production`

#### Updating Your Deployment

To update with new code changes:
```bash
# Rebuild container
gcloud builds submit --tag gcr.io/$PROJECT_ID/streets-editor:v2 --no-cache .

# Update service
gcloud run deploy streets-editor --image gcr.io/$PROJECT_ID/streets-editor:v2
```

## License

MIT
