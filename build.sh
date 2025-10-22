PROJECT_ID=$(gcloud config get project)
REGION=us-central1
USE_MEDIA_PROXY=false
gcloud builds submit . --project=$PROJECT_ID --gcs-source-staging-dir=gs://run-resources-$PROJECT_ID-$REGION/services/creative-studio --region=$REGION --service-account=projects/$PROJECT_ID/serviceAccounts/builds-creative-studio@$PROJECT_ID.iam.gserviceaccount.com --set-env-var USE_MEDIA_PROXY=${USE_MEDIA_PROXY}
