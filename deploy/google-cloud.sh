#!/usr/bin/env bash
set -euo pipefail
: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your own billing-enabled project}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${AFTERCARE_SERVICE:-aftercare}"
DATABASE="${FIRESTORE_DATABASE:-aftercare}"
RUNTIME="aftercare-runtime@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com --project "$GOOGLE_CLOUD_PROJECT"
# Provision the named database and dedicated identity first with setup-google-cloud.sh.
gcloud run deploy "$SERVICE" --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --source . --service-account "$RUNTIME" --allow-unauthenticated --no-cpu-throttling --memory 512Mi --cpu 1 --min-instances 0 --max-instances 1 --concurrency 20 --timeout 300 --set-env-vars "DATA_DIR=/tmp/aftercare,COOKIE_SECURE=true,AFTERCARE_STORE=firestore,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,FIRESTORE_DATABASE=$DATABASE"
URL="$(gcloud run services describe "$SERVICE" --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --format='value(status.url)')"
gcloud run services update "$SERVICE" --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --update-env-vars "APP_ORIGIN=$URL" --quiet
printf '\nAftercare: %s\n' "$URL"
