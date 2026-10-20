#!/usr/bin/env bash
set -euo pipefail
: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your own billing-enabled project}"
DATABASE="${FIRESTORE_DATABASE:-aftercare}"
RUNTIME="aftercare-runtime@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com --project "$GOOGLE_CLOUD_PROJECT"
if ! gcloud firestore databases describe --project "$GOOGLE_CLOUD_PROJECT" --database "$DATABASE" >/dev/null 2>&1; then
  gcloud firestore databases create --project "$GOOGLE_CLOUD_PROJECT" --database "$DATABASE" --location nam5 --type firestore-native --delete-protection
fi
if ! gcloud iam service-accounts describe "$RUNTIME" --project "$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create aftercare-runtime --project "$GOOGLE_CLOUD_PROJECT" --display-name 'Aftercare isolated runtime'
fi
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" --member "serviceAccount:$RUNTIME" --role roles/datastore.user --condition "expression=resource.name==\"projects/$GOOGLE_CLOUD_PROJECT/databases/$DATABASE\",title=aftercare-database-only,description=Access only Aftercare named database" --quiet
