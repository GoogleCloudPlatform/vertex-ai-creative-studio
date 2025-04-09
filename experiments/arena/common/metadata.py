# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
from typing import Optional, Dict, Any, List
import pandas as pd

from google.cloud import firestore

from config.default import Default
from config.firebase_config import FirebaseClient
from config.spanner_config import ArenaStudyTracker, ArenaModelEvaluation
from models.set_up import ModelSetup
from common.storage import check_gcs_blob_exists
from alive_progress import alive_bar

from utils.logger import LogLevel, log


# Initialize configuration
client, model_id = ModelSetup.init()
MODEL_ID = model_id
config = Default()
db = FirebaseClient(database_id=config.IMAGE_FIREBASE_DB).get_client()


def add_image_metadata(gcsuri: str, prompt: str, model: str, study: Optional[str] = "live", collection_name: Optional[str] = None):
    """Add Image metadata to Firestore persistence"""
    
    if collection_name is None:
        collection_name = config.IMAGE_COLLECTION_NAME
    print(f"Using Firestore collection: {collection_name}")
    current_datetime = datetime.datetime.now()

    # Store the image metadata in Firestore
    doc_ref = db.collection(collection_name).document()
    try:
        doc_ref.set(
            {
                "gcsuri": gcsuri,
                "study": study,
                "prompt": prompt,
                "model": model,
                "timestamp": current_datetime,  # alt: firestore.SERVER_TIMESTAMP
            }
        )
    except Exception as e:
        print(f"Error storing image metadata: {e}")
        return
    print(f"Image data stored in Firestore with document ID: {doc_ref.id}")


def load_metadata_from_json(
    collection_name: str,
    json_file_path: str,
    top_level_key: str,
    gcs_sub_folder: str,
    model_name: str,
    key_mapping: Optional[Dict[Any, str]] = None,
) -> None:
    """
    Loads metadata from a JSON file and adds it to Firestore using add_image_metadata,
    with a progress bar.

    Args:
        collection_name: The name of the Firestore collection to store metadata in.
        json_file_path: Path to the JSON file containing the metadata.
        top_level_key: The key in the JSON that contains the list of metadata entries.
        gcs_sub_folder: The sub-folder within the GCS bucket where the images are located.
        model_name: The model to associate with the metadata entries.
        key_mapping: An optional dictionary to map keys (or indices) from the JSON structure
                     to the expected arguments of `add_image_metadata`.
                     For the given example, it would be `{0: 'prompt', 1: 'images'}`.
                     The value associated with 'images' is expected to be a list of image identifiers.
    """
    if key_mapping is None:
        key_mapping = {0: "prompt", 1: "images"}

    # Validate: Ensure the file exists
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"Metadata file not found: {json_file_path}")

    with open(json_file_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        data_list = metadata.get(top_level_key, [])

        if not data_list:
            raise ValueError(f"No data found under the key '{top_level_key}' in the provided JSON file.")

        total_items = len(data_list)
        with alive_bar(total_items, title="Processing Metadata") as bar:
            for item in data_list:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    print(f"Skipping invalid item format: {item}. Expected a list or tuple with at least two elements.")
                    bar()  # Increment the progress bar
                    continue

                prompt_key = key_mapping.get(0)
                images_key = key_mapping.get(1)

                if prompt_key is None or images_key is None:
                    raise ValueError("Key mapping must include keys for both 'prompt' (typically index 0) and 'images' (typically index 1).")

                prompt = item[0]
                images = item[1]

                if prompt is None:
                    print(f"Skipping item with missing prompt: {item}")
                    bar()  # Increment the progress bar
                    continue

                if not isinstance(images, list) or not images:
                    print(f"No images found for prompt: '{prompt}'. Skipping...")
                    bar()  # Increment the progress bar
                    continue

                print(f"Processing prompt: 'Found {len(images)} potential {'image' if len(images) == 1 else 'images'}...")
                print(f"Images ID(s): {images}")
                print(f"Sub-folder: {gcs_sub_folder}")
                print(f"Model: {model_name}")
                selected_image = None
                for image_id in images:
                    gcs_uri = f"gs://{Default.GENMEDIA_BUCKET}/{gcs_sub_folder}/{image_id}"
                    if check_gcs_blob_exists(gcs_uri):
                        print(f"Selected image: {image_id} exists in GCS.")
                        selected_image = image_id
                        selected_image_gcsuri = gcs_uri
                        break
                else:
                    print(f"No valid images found in GCS for prompt: '{prompt}'. Skipping...")
                    bar()  # Increment the progress bar
                    continue

                print(f"Adding metadata for prompt: '{prompt}' with image URI: {selected_image_gcsuri}...")
                add_image_metadata(collection_name=collection_name, gcsuri=selected_image_gcsuri, prompt=prompt, model=model_name)
                bar()  # Increment the progress bar

def get_elo_ratings(study: str):
    """ Retrieve ELO ratings for models from Firestore """
    # Fetch current ELO ratings from Firestore
    doc_ref = (
        db.collection(config.IMAGE_RATINGS_COLLECTION_NAME)
        .where(filter=firestore.FieldFilter("study", "==", study))
        .where(filter=firestore.FieldFilter("type", "==", "elo_rating"))
        .get()
    )
    updated_ratings = {}
    if doc_ref:
        for doc in doc_ref:
            ratings = doc.to_dict().get("ratings", {})
            updated_ratings.update(ratings)
    # Convert to DataFrame
    df = pd.DataFrame(list(updated_ratings.items()), columns=['Model', 'ELO Rating'])
    df = df.sort_values(by='ELO Rating', ascending=False)  # Sort by rating
    df.reset_index(drop=True, inplace=True)  # Reset index
    return df


def update_elo_ratings(model1: str, model2: str, winner: str, images: list[str], prompt: str, study: str):
    """Update ELO ratings for models"""

    current_datetime = datetime.datetime.now()

    # Fetch current ELO ratings from Firestore
    doc_ref = (
        db.collection(config.IMAGE_RATINGS_COLLECTION_NAME)
        .where(filter=firestore.FieldFilter("study", "==", study))
        .where(filter=firestore.FieldFilter("type", "==", "elo_rating"))
        .get()
    )

    updated_ratings = {}
    elo_rating_doc_id = None  # Store the document ID
    if doc_ref:
        for doc in doc_ref:
            elo_rating_doc_id = doc.id  # Get the document ID
            ratings = doc.to_dict().get("ratings", {})
            updated_ratings.update(ratings)

    elo_model1 = updated_ratings.get(model1, 1000)  # Default to 1000 if not found
    elo_model2 = updated_ratings.get(model2, 1000)

    # Calculate expected scores
    expected_model1 = 1 / (1 + 10 ** ((elo_model2 - elo_model1) / 400))
    expected_model2 = 1 / (1 + 10 ** ((elo_model1 - elo_model2) / 400))

    # Update ELO ratings based on the winner
    k_factor = config.ELO_K_FACTOR
    if winner == model1:
        elo_model1 = elo_model1 + k_factor * (1 - expected_model1)
        elo_model2 = elo_model2 + k_factor * (0 - expected_model2)
    elif winner == model2:
        elo_model1 = elo_model1 + k_factor * (0 - expected_model1)
        elo_model2 = elo_model2 + k_factor * (1 - expected_model2)

    updated_ratings[model1] = round(elo_model1, 2)
    updated_ratings[model2] = round(elo_model2, 2)

    print(f"Ratings: {updated_ratings}")

    # Store updated ELO ratings in Firestore
    if elo_rating_doc_id:  # Check if the document ID was found
        doc_ref = db.collection(config.IMAGE_RATINGS_COLLECTION_NAME).document(elo_rating_doc_id)
        doc_ref.update(
            {
                "ratings": updated_ratings,
                "timestamp": current_datetime,
            }
        )
        print(f"ELO ratings updated in Firestore with document ID: {doc_ref.id}")
    else:
        # Document doesn't exist, create it
        doc_ref = db.collection(config.IMAGE_RATINGS_COLLECTION_NAME).document()
        doc_ref.set(
            {
                "study": study,
                "type": "elo_rating",
                "ratings": updated_ratings,
                "timestamp": current_datetime,
            }
        )

        print(f"ELO ratings created in Firestore with document ID: {doc_ref.id}")

    doc_ref = db.collection(config.IMAGE_RATINGS_COLLECTION_NAME).document()
    doc_ref.set(
        {
            "timestamp": current_datetime,
            "type": "vote",
            "model1": model1,
            "image1": images[0],
            "model2": model2,
            "image2": images[1],
            "winner": winner,
            "prompt": prompt,
            "study": study
        }
    )

    print(f"Vote updated in Firestore with document ID: {doc_ref.id}")

    # Update the latest ELO ratings in Spanner
    study_tracker = ArenaStudyTracker(
        project_id=config.PROJECT_ID,
        spanner_instance_id=config.SPANNER_INSTANCE_ID,
        spanner_database_id=config.SPANNER_DATABASE_ID,
    )
    if not study_tracker:
        log("Failed to initialize Spanner study tracker.", LogLevel.ERROR)
        raise RuntimeError("Spanner study tracker initialization failed.")
    elo_ratings_by_model = []
    for model, elo in updated_ratings.items():
        elo_study_entry = ArenaModelEvaluation(model_name=model, 
                             rating=elo, 
                             study=study)
        elo_ratings_by_model.append(elo_study_entry)
    
    try:
        study_tracker.upsert_study_runs(study_runs=elo_ratings_by_model)
        log(f"ELO ratings updated in Spanner for study '{study}'.", LogLevel.ON)
    except Exception as e:
        log(f"Failed to update ELO ratings in Spanner: {e}", LogLevel.ERROR)
        raise RuntimeError(f"Failed to update ELO ratings in Spanner: {e}")


def get_latest_votes(study: str, limit: int = 10):
    """Retrieve the latest votes from Firestore, ordered by timestamp in descending order."""

    try:
        votes_ref = (
            db.collection(config.IMAGE_RATINGS_COLLECTION_NAME)
            .where(filter=firestore.FieldFilter("study", "==", study))
            .where(filter=firestore.FieldFilter("type", "==", "vote"))
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )

        votes = []
        for doc in votes_ref.stream():
            votes.append(doc.to_dict())

        return votes

    except Exception as e:
        print(f"Error fetching votes: {e}")
        return []
