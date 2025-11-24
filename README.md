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

### AI Integration
- OpenRouter.ai for accessing AI models
- Gemini 2.5 Pro for street extraction

## Setup

### Prerequisites

- Python 3.11+
- OpenRouter API key
- Neon account (for production and testing databases)
- Docker (for local development)

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
- `SECRET_KEY`: Your Flask secret key
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `DATABASE_URL`: Your Neon production database URL (main branch)
- `DATABASE_URL_E2E`: Your Neon e2e testing database URL (e2e-testing branch)

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
3. Wait for AI extraction (≤ 5 minutes)
4. Review and edit extracted streets
5. Export your dictionary as TXT or JSON

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

## Testing

Run tests with pytest:

```bash
pytest
```

## License

MIT
