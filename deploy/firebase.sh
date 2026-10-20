#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your billing-enabled project}"
SITE="${FIREBASE_SITE:-aftercare-release}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${AFTERCARE_SERVICE:-aftercare}"
DATABASE="${FIRESTORE_DATABASE:-aftercare}"
RUNTIME="aftercare-runtime@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
gcloud services enable firebase.googleapis.com firebasehosting.googleapis.com run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com --project "$GOOGLE_CLOUD_PROJECT" --quiet
npm --prefix web ci
npm --prefix web run build
EXISTING_URL="$(gcloud run services describe "$SERVICE" --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --format='value(status.url)' 2>/dev/null || true)"
ORIGINS="https://${SITE}.web.app,https://${SITE}.firebaseapp.com"
if [[ -n "$EXISTING_URL" ]]; then ORIGINS="$ORIGINS,$EXISTING_URL"; fi
gcloud run deploy "$SERVICE" --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --source . --service-account "$RUNTIME" --allow-unauthenticated --no-cpu-throttling --memory 512Mi --cpu 1 --min-instances 0 --max-instances 1 --concurrency 20 --timeout 300 --set-env-vars "^|^DATA_DIR=/tmp/aftercare|COOKIE_SECURE=true|AFTERCARE_STORE=firestore|GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT|FIRESTORE_DATABASE=$DATABASE|APP_ORIGIN=https://${SITE}.web.app|APP_ORIGINS=$ORIGINS" --quiet
python3 deploy/firebase-hosting.py --project "$GOOGLE_CLOUD_PROJECT" --site "$SITE" --skip-build
