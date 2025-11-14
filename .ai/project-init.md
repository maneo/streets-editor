⏺ Based on the tech stack and PRD, here's a comprehensive project setup for your Streets Dictionary Editor:

  Recommended Folder Structure

  streets-editor/
  ├── app/
  │   ├── __init__.py              # Flask app factory
  │   ├── config.py                # Configuration classes
  │   ├── models/
  │   │   ├── __init__.py
  │   │   ├── user.py              # User model (Flask-Login)
  │   │   └── street.py            # Street dictionary models
  │   ├── routes/
  │   │   ├── __init__.py
  │   │   ├── auth.py              # Registration & login
  │   │   ├── upload.py            # File upload & extraction
  │   │   └── export.py            # TXT/JSON export
  │   ├── services/
  │   │   ├── __init__.py
  │   │   ├── ai_extraction.py     # OpenRouter/Gemini integration
  │   │   ├── file_handler.py      # Image upload validation
  │   │   └── export_service.py    # Export logic
  │   ├── static/
  │   │   ├── css/
  │   │   │   └── input.css        # Tailwind input file
  │   │   ├── js/
  │   │   │   ├── upload.js        # Upload handling
  │   │   │   └── editor.js        # Street list editor
  │   │   └── uploads/             # Temporary upload storage
  │   └── templates/
  │       ├── base.html            # Base layout with Tailwind
  │       ├── auth/
  │       │   ├── login.html
  │       │   └── register.html
  │       ├── upload.html          # Upload form
  │       └── editor.html          # Street list editor
  ├── migrations/                   # SQLAlchemy migrations (Alembic)
  ├── tests/
  │   ├── __init__.py
  │   ├── test_auth.py
  │   ├── test_extraction.py
  │   └── test_export.py
  ├── .env.example                 # Environment variables template
  ├── .env                         # Actual env vars (gitignored)
  ├── .gitignore
  ├── requirements.txt             # Python dependencies
  ├── Dockerfile                   # Docker image for deployment
  ├── docker-compose.yml           # Local development with Docker
  ├── tailwind.config.js           # Tailwind 4 configuration
  ├── run.py                       # Application entry point
  └── README.md

  Python Packages to Install

  Create requirements.txt:
  # Flask & Extensions
  Flask==3.0.0
  Flask-Login==0.6.3
  Flask-SQLAlchemy==3.1.1
  Flask-Migrate==4.0.5

  # Database
  SQLAlchemy==2.0.23

  # Authentication & Security
  Werkzeug==3.0.1
  python-dotenv==1.0.0

  # Image Processing
  Pillow==10.1.0

  # AI Integration
  requests==2.31.0
  httpx==0.25.2

  # File Handling
  python-magic==0.4.27

  # Development
  pytest==7.4.3
  pytest-flask==1.3.0
  black==23.12.1
  flake8==6.1.0

  Initial Configuration Files

  .env.example

  FLASK_APP=run.py
  FLASK_ENV=development
  SECRET_KEY=your-secret-key-here
  DATABASE_URL=sqlite:///streets_editor.db
  OPENROUTER_API_KEY=your-openrouter-key
  MAX_UPLOAD_SIZE=52428800
  UPLOAD_FOLDER=app/static/uploads

  tailwind.config.js

  /** @type {import('tailwindcss').Config} */
  module.exports = {
    content: [
      "./app/templates/**/*.html",
      "./app/static/js/**/*.js",
    ],
    theme: {
      extend: {},
    },
    plugins: [],
  }

  Dockerfile

  FROM python:3.11-slim

  WORKDIR /app

  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      libmagic1 \
      && rm -rf /var/lib/apt/lists/*

  # Copy requirements and install Python dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy application code
  COPY . .

  # Expose port
  EXPOSE 5000

  # Run the application
  CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]

  .gitignore

  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  *.so
  .Python
  venv/
  env/
  ENV/

  # Flask
  instance/
  .webassets-cache

  # Database
  *.db
  *.sqlite

  # Environment
  .env

  # Uploads
  app/static/uploads/*
  !app/static/uploads/.gitkeep

  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo

  # Tailwind
  node_modules/
  app/static/css/output.css

  # Testing
  .pytest_cache/
  .coverage
  htmlcov/

  Installation Steps

  # 1. Create virtual environment
  python3 -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate

  # 2. Install Python packages
  pip install -r requirements.txt

  # 3. Install Tailwind CSS (requires Node.js)
  npm install -D tailwindcss
  npx tailwindcss init

  # 4. Setup environment variables
  cp .env.example .env
  # Edit .env with your actual values

  # 5. Initialize database
  flask db init
  flask db migrate -m "Initial migration"
  flask db upgrade

  # 6. Build Tailwind CSS
  npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --watch

  Key Initial Files to Create

  1. run.py - Entry point:
  from app import create_app

  app = create_app()

  if __name__ == '__main__':
      app.run(debug=True)

  2. app/__init__.py - App factory with Flask-Login setup
  3. app/config.py - Configuration classes (Development, Production)
  4. app/models/user.py - User model with password hashing
  5. app/models/street.py - Street, Session models
  6. app/services/ai_extraction.py - OpenRouter API integration

  This structure follows Flask best practices, separates concerns clearly, and sets you up for the CI/CD pipeline with GitHub Actions and Docker deployment to
  DigitalOcean.
  
