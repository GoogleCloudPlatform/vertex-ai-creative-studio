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
"""metadata implementation"""

import datetime

# from models.model_setup import ModelSetup
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd
from google.cloud import firestore

from config.default import Default
from config.firebase_config import FirebaseClient

# Initialize configuration
# client, model_id = ModelSetup.init()
# MODEL_ID = model_id
config = Default()
db = FirebaseClient(database_id=config.GENMEDIA_FIREBASE_DB).get_client()


@dataclass
class MediaItem:
    """Represents a single media item in the library."""

    id: Optional[str] = None
    aspect: Optional[str] = None
    gcsuri: Optional[str] = None
    prompt: Optional[str] = None
    generation_time: Optional[float] = None
    timestamp: Optional[str] = None
    reference_image: Optional[str] = None
    last_reference_image: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    mime_type: Optional[str] = None
    rewritten_prompt: Optional[str] = None
    model: Optional[str] = None
    raw_data: Optional[Dict] = field(
        default_factory=dict
    )  # To store the raw Firestore document


def get_media_item_by_id(
    item_id: str,
) -> Optional[MediaItem]:  # Assuming MediaItem class is defined/imported
    """Retrieve a specific media item by its Firestore document ID."""
    try:
        print(f"Trying to retrieve {item_id}")
        doc_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).document(item_id)
        doc = doc_ref.get()
        if doc.exists:
            raw_item_data = doc.to_dict()
            if raw_item_data is None:
                print(
                    f"Warning: doc.to_dict() returned None for existing doc ID: {doc.id}"
                )
                return None

            timestamp_iso_str: Optional[str] = None
            raw_timestamp = raw_item_data.get("timestamp")
            if isinstance(raw_timestamp, datetime):
                timestamp_iso_str = raw_timestamp.isoformat()
            elif isinstance(raw_timestamp, str):
                timestamp_iso_str = raw_timestamp
            elif hasattr(
                raw_timestamp, "isoformat"
            ):  # Handle Firestore Timestamp objects
                timestamp_iso_str = raw_timestamp.isoformat()

            try:
                gen_time = (
                    float(raw_item_data.get("generation_time"))
                    if raw_item_data.get("generation_time") is not None
                    else None
                )
            except (ValueError, TypeError):
                gen_time = None

            try:
                item_duration = (
                    float(raw_item_data.get("duration"))
                    if raw_item_data.get("duration") is not None
                    else None
                )
            except (ValueError, TypeError):
                item_duration = None

            media_item = MediaItem(
                id=doc.id,
                model=str(raw_item_data.get("model"))
                if raw_item_data.get("model") is not None
                else None,
                aspect=str(raw_item_data.get("aspect"))
                if raw_item_data.get("aspect") is not None
                else None,
                gcsuri=str(raw_item_data.get("gcsuri"))
                if raw_item_data.get("gcsuri") is not None
                else None,
                prompt=str(raw_item_data.get("prompt"))
                if raw_item_data.get("prompt") is not None
                else None,
                generation_time=gen_time,
                timestamp=timestamp_iso_str,
                reference_image=str(raw_item_data.get("reference_image"))
                if raw_item_data.get("reference_image") is not None
                else None,
                last_reference_image=str(raw_item_data.get("last_reference_image"))
                if raw_item_data.get("last_reference_image") is not None
                else None,
                enhanced_prompt=str(raw_item_data.get("enhanced_prompt"))
                if raw_item_data.get("enhanced_prompt") is not None
                else None,
                duration=item_duration,
                error_message=str(raw_item_data.get("error_message"))
                if raw_item_data.get("error_message") is not None
                else None,
                rewritten_prompt=str(raw_item_data.get("rewritten_prompt"))
                if raw_item_data.get("rewritten_prompt") is not None
                else None,
                raw_data=raw_item_data,
            )
            return media_item
        else:
            print(f"No document found with ID: {item_id}")
            return None
    except Exception as e:
        print(f"Error fetching media item by ID {item_id}: {e}")
        return None


def add_music_metadata(
    model: str,
    gcsuri: str,
    prompt: str,
    original_prompt: str,
    rewritten_prompt: str,
    generation_time: float,
    error_message: str,
    audio_analysis: str,
):
    """Add Music metadata to Firestore persistence"""
    current_datetime = datetime.datetime.now()

    # Store the image metadata in Firestore
    doc_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).document()
    doc_ref.set(
        {
            "gcsuri": gcsuri,
            "prompt": prompt,
            "original_prompt": original_prompt,
            "rewritten_prompt": rewritten_prompt,
            # "duration"
            "model": model,
            # "duration": duration,
            "generation_time": generation_time,
            "mime_type": "audio/wav",
            "error_message": error_message,
            "audio_analysis": audio_analysis,
            # "comment": comment,
            "timestamp": current_datetime,  # alt: firestore.SERVER_TIMESTAMP
        }
    )

    print(f"Music data stored in Firestore with document ID: {doc_ref.id}")


def add_video_metadata(
    gcsuri: str,
    prompt: str,
    aspect_ratio: str,
    model: str,
    generation_time: float,
    duration: int,
    reference_image: str,
    rewrite_prompt: bool,
    error_message: str,
    comment: str,
    last_reference_image: str,
):
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
            "last_reference_image": last_reference_image,
            "enhanced_prompt": rewrite_prompt,
            "mime_type": "video/mp4",
            "error_message": error_message,
            "comment": comment,
            "timestamp": current_datetime,  # alt: firestore.SERVER_TIMESTAMP
        }
    )

    print(f"Video data stored in Firestore with document ID: {doc_ref.id}")


def get_latest_videos(limit: int = 10):
    """Retrieve the last 10 videos"""
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


def get_total_media_count():
    """get count of all media in firestore"""
    media_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    )
    count = len([doc.to_dict() for doc in media_ref.stream()])
    return count
