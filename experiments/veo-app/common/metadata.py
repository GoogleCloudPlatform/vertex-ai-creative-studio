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
""" metadata implementation """
import datetime
import pandas as pd

from google.cloud import firestore

from config.default import Default
from config.firebase_config import FirebaseClient
#from models.model_setup import ModelSetup


# Initialize configuration
#client, model_id = ModelSetup.init()
#MODEL_ID = model_id
config = Default()
db = FirebaseClient(database_id=config.GENMEDIA_FIREBASE_DB).get_client()


def add_video_metadata(gcsuri: str, prompt: str, aspect_ratio: str, model: str, generation_time: float, duration: int, reference_image: str, rewrite_prompt: bool, error_message: str, comment: str):
    """Add Video metadata to Firestore persistence"""

    current_datetime = datetime.datetime.now()

    # Store the image metadata in Firestore
    doc_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).document()
    doc_ref.set(
        {
            "gcsuri": gcsuri,
            "prompt": prompt,
            "model": model,
            "aspect": aspect_ratio,
            "duration": duration,
            "generation_time": generation_time,
            "reference_image": reference_image,
            "enhanced_prompt": rewrite_prompt,
            "mime_type": "video/mp4",
            "error_message": error_message,
            "comment": comment,
            "timestamp": current_datetime,  # alt: firestore.SERVER_TIMESTAMP
        }
    )

    print(f"Video data stored in Firestore with document ID: {doc_ref.id}")


def get_latest_videos(limit: int = 10):
    """ Retrieve the last 10 videos """
    try:
        media_ref = (
            db.collection(config.GENMEDIA_COLLECTION_NAME)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        media = []
        for doc in media_ref.stream():
            media.append(doc.to_dict())

        return media
    except Exception as e:
        print(f"Error fetching media: {e}")
        return []