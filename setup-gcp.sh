#!/bin/bash

# Google Cloud Setup Script for Streets Editor Deployment
# This script helps set up Google Cloud resources needed for deployment

set -e

echo "🚀 Streets Editor - Google Cloud Setup"
echo "====================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
    echo "❌ Not authenticated with Google Cloud. Please run:"
    echo "   gcloud auth login"
    exit 1
fi

# Get project ID
echo "Enter your Google Cloud Project ID:"
read -r PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID cannot be empty"
    exit 1
fi

echo "Setting project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

echo ""
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com

echo ""
echo "🪣 Creating Cloud Storage buckets..."

# Create buckets for different environments
BUCKETS=("streets-editor-dev" "streets-editor-test" "streets-editor-prod")

for bucket in "${BUCKETS[@]}"; do
    if gsutil ls -b gs://$bucket &> /dev/null; then
        echo "Bucket gs://$bucket already exists. Skipping creation..."
    else
        echo "Creating bucket: gs://$bucket"
        gsutil mb -p "$PROJECT_ID" gs://$bucket
    fi
done

echo ""
echo "🔓 Configuring public access for buckets..."

# Configure public read access for all buckets
for bucket in "${BUCKETS[@]}"; do
    echo "Setting public read access for gs://$bucket"
    gsutil iam ch allUsers:objectViewer gs://$bucket
done

echo ""
echo "⚙️  Enabling uniform bucket-level access..."

# Enable uniform bucket-level access (recommended for new buckets)
for bucket in "${BUCKETS[@]}"; do
    echo "Enabling uniform access for gs://$bucket"
    gsutil bucketpolicyonly set on gs://$bucket
done

echo ""
echo "👤 Creating service account for GitHub Actions..."

# Create service account
SA_NAME="streets-editor-deployer"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Check if service account already exists
if gcloud iam service-accounts describe "$SA_EMAIL" &> /dev/null; then
    echo "Service account $SA_EMAIL already exists. Skipping creation..."
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Streets Editor Deployer"
fi

echo ""
echo "🔑 Assigning roles to service account..."

# Assign necessary roles
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudbuild.builds.builder"

echo ""
echo "🔐 Creating service account key..."
echo "⚠️  WARNING: This key will be displayed below. Copy it immediately and add to GitHub Secrets!"
echo ""

gcloud iam service-accounts keys create /tmp/sa-key.json \
    --iam-account="$SA_EMAIL"

echo "📋 Service Account Key (add this to GitHub Secret 'GCP_SA_KEY'):"
echo "================================================================="
cat /tmp/sa-key.json
echo ""
echo "================================================================="

# Clean up
rm -f /tmp/sa-key.json

echo ""
echo "✅ Setup complete!"
echo "   ✓ Service account created and configured"
echo "   ✓ Cloud Storage buckets created and configured for public access"
echo "   ✓ All required APIs enabled"
echo ""
echo "📝 Add these secrets to your GitHub repository:"
echo "   1. GCP_SA_KEY: The JSON key shown above"
echo "   2. GCP_PROJECT_ID: $PROJECT_ID"
echo "   3. GCS_BUCKET_DEV: streets-editor-dev"
echo "   4. GCS_BUCKET_TEST: streets-editor-test"
echo "   5. GCS_BUCKET_PROD: streets-editor-prod"
echo "   6. GCP_REGION: Your preferred region (e.g., europe-west1)"
echo "   7. DATABASE_URL: Your Neon database connection string"
echo "   8. FLASK_SECRET_KEY: Generate with 'openssl rand -hex 32'"
echo "   9. OPENROUTER_API_KEY: Your OpenRouter API key"
echo ""
echo "🚀 You're ready to deploy! Go to GitHub Actions and run the 'Deploy to Google Cloud Run' workflow."
