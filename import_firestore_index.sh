#!/bin/bash
# This script imports the Firestore index into the Terraform state.
set -e # Exit immediately if a command exits with a non-zero status.

PROJECT_ID="generative-bazaar-001"

echo "Importing Firestore index..."
terraform import 'google_firestore_index.genmedia_library_mime_type_timestamp' "projects/$PROJECT_ID/databases/(default)/collectionGroups/genmedia/indexes/"`terraform plan -no-color | grep "name:" | grep -o -E '[a-zA-Z0-9_]+' | head -n 1`""

echo "Firestore index imported successfully."
