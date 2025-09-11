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
    """Represents a single media item in the library for Firestore storage and retrieval."""

    id: Optional[str] = None  # Firestore document ID
    related_media_item_id: Optional[str] = None # For linking generation sequences
    user_email: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None # Store as datetime object

    # Common fields across media types
    prompt: Optional[str] = None  # The final prompt used for generation
    original_prompt: Optional[str] = None  # User's initial prompt if rewriting occurred
    rewritten_prompt: Optional[str] = None  # The prompt after any rewriter (Gemini, etc.)
    model: Optional[str] = None # Specific model ID used (e.g., "imagen-3.0-fast", "veo-2.0")
    mime_type: Optional[str] = None # e.g., "video/mp4", "image/png", "audio/wav"
    generation_time: Optional[float] = None  # Seconds for generation
    error_message: Optional[str] = None # If any error occurred during generation

    # URI fields
    gcsuri: Optional[str] = None  # For single file media (video, audio) -> gs://bucket/path
    gcs_uris: List[str] = field(default_factory=list)  # For multi-file media (e.g., multiple images) -> list of gs://bucket/path
    source_images_gcs: List[str] = field(default_factory=list) # For multi-file input media (e.g., recontext) -> list of gs://bucket/path

    # Video specific (some may also apply to Image/Audio)
    aspect: Optional[str] = None  # e.g., "16:9", "1:1" (also for Image)
    resolution: Optional[str] = None # e.g., "720p", "1080p"
    duration: Optional[float] = None  # Seconds (also for Audio)
    reference_image: Optional[str] = None
    last_reference_image: Optional[str] = None
    negative_prompt: Optional[str] = None
    enhanced_prompt_used: bool = False
    comment: Optional[str] = None # General comment field, e.g., for video generation type

    # Image specific
    # aspect is shared with Video
    modifiers: List[str] = field(default_factory=list) # e.g., ["photorealistic", "wide angle"]
    negative_prompt: Optional[str] = None
    num_images: Optional[int] = None # Number of images generated in a batch
    seed: Optional[int] = None # Seed used for generation (also potentially for video/audio)
    critique: Optional[str] = None # Gemini-generated critique for images

    # Music specific
    # duration is shared with Video
    audio_analysis: Optional[Dict] = None # Structured analysis from Gemini, stored as a map

    # This field is for loading raw data from Firestore, not for writing.
    # It helps in debugging and displaying all stored fields if needed.
    raw_data: Optional[Dict] = field(default_factory=dict, compare=False, repr=False)

    # Character Consistency specific fields
    media_type: Optional[str] = None
    source_character_images: List[str] = field(default_factory=list)
    character_description: Optional[str] = None
    imagen_prompt: Optional[str] = None
    veo_prompt: Optional[str] = None
    candidate_images: List[str] = field(default_factory=list)
    best_candidate_image: Optional[str] = None
    outpainted_image: Optional[str] = None

    # Chirp and Gemini-TTS specific fields
    custom_pronunciations: List[dict[str, str]] = field(default_factory=list)
    voice: Optional[str] = None
    pace: Optional[float] = None
    volume_gain_db: Optional[float] = None
    language_code: Optional[str] = None
    style_prompt: Optional[str] = None




def add_media_item_to_firestore(item: MediaItem):
    """Adds a MediaItem to Firestore. Sets timestamp if not already present."""
    if not db:
        print("Firestore client (db) is not initialized. Cannot add media item.")
        # Or raise an exception: raise ConnectionError("Firestore client not initialized")
        return

    # Prepare data for Firestore, excluding None values and the 'id' field
    firestore_data = {}
    for f in field_names(item):
        if f == "id":  # Exclude id from direct storage
            continue
        value = getattr(item, f)
        if value is not None:
            if f == "timestamp" and isinstance(value, str): # If timestamp is already string, try to parse
                try:
                    firestore_data[f] = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    print(f"Warning: Could not parse timestamp string '{value}' to datetime. Storing as is or consider handling.")
                    firestore_data[f] = value # Or handle error, or ensure it's always datetime
            else:
                firestore_data[f] = value

    # Ensure timestamp is set
    if "timestamp" not in firestore_data or firestore_data["timestamp"] is None:
        firestore_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(firestore_data["timestamp"], datetime.datetime) and firestore_data["timestamp"].tzinfo is None:
        # If datetime is naive, assume UTC (or local, then convert to UTC)
        # For consistency, Firestore often expects UTC.
        firestore_data["timestamp"] = firestore_data["timestamp"].replace(tzinfo=datetime.timezone.utc)


    try:
        doc_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).document()
        doc_ref.set(firestore_data)
        item.id = doc_ref.id # Set the ID back to the item
        print(f"MediaItem data stored in Firestore with document ID: {doc_ref.id}")
        print(f"Stored data: {firestore_data}")
    except Exception as e:
        print(f"Error storing MediaItem to Firestore: {e}")
        # Optionally re-raise or handle more gracefully
        raise

def field_names(dataclass_instance):
    """Helper to get field names of a dataclass instance."""
    return [f.name for f in dataclass_instance.__dataclass_fields__.values()]

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
            if isinstance(raw_timestamp, str):
                timestamp_iso_str = raw_timestamp
            elif hasattr(raw_timestamp, "isoformat"):  # Handles both datetime and firestore.Timestamp
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
                gcs_uris=raw_item_data.get("gcs_uris", []),
                prompt=str(raw_item_data.get("original_prompt"))
                if raw_item_data.get("original_prompt") is not None
                else str(raw_item_data.get("prompt")),
                generation_time=gen_time,
                timestamp=timestamp_iso_str,
                reference_image=str(raw_item_data.get("reference_image"))
                if raw_item_data.get("reference_image") is not None
                else None,
                last_reference_image=str(raw_item_data.get("last_reference_image"))
                if raw_item_data.get("last_reference_image") is not None
                else None,
                negative_prompt=str(raw_item_data.get("negative_prompt"))
                if raw_item_data.get("negative_prompt") is not None
                else None,
                enhanced_prompt_used=raw_item_data.get("enhanced_prompt_used", False),
                duration=item_duration,
                error_message=str(raw_item_data.get("error_message"))
                if raw_item_data.get("error_message") is not None
                else None,
                rewritten_prompt=str(raw_item_data.get("rewritten_prompt"))
                if raw_item_data.get("rewritten_prompt") is not None
                else None,
                critique=str(raw_item_data.get("critique"))
                if raw_item_data.get("critique") is not None
                else None,
                resolution=str(raw_item_data.get("resolution"))
                if raw_item_data.get("resolution") is not None
                else None,
                media_type=str(raw_item_data.get("media_type"))
                if raw_item_data.get("media_type") is not None
                else None,
                source_character_images=raw_item_data.get("source_character_images", []),
                character_description=str(raw_item_data.get("character_description"))
                if raw_item_data.get("character_description") is not None
                else None,
                imagen_prompt=str(raw_item_data.get("imagen_prompt"))
                if raw_item_data.get("imagen_prompt") is not None
                else None,
                veo_prompt=str(raw_item_data.get("veo_prompt"))
                if raw_item_data.get("veo_prompt") is not None
                else None,
                candidate_images=raw_item_data.get("candidate_images", []),
                best_candidate_image=str(raw_item_data.get("best_candidate_image"))
                if raw_item_data.get("best_candidate_image") is not None
                else None,
                outpainted_image=str(raw_item_data.get("outpainted_image"))
                if raw_item_data.get("outpainted_image") is not None
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


def add_media_item(user_email: str, **kwargs):
    """Add a media item to Firestore persistence"""

    current_datetime = datetime.datetime.now(datetime.timezone.utc)

    # Prepare data for Firestore
    firestore_data = {
        "user_email": user_email,
        "timestamp": current_datetime,
    }

    # Merge kwargs into firestore_data
    firestore_data.update(kwargs)

    doc_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).document()
    doc_ref.set(firestore_data)

    print(f"Media data stored in Firestore with document ID: {doc_ref.id}")


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

def add_vto_metadata(
    person_image_gcs: str,
    product_image_gcs: str,
    result_image_gcs: list[str],
    user_email: str,
):
    """Add VTO metadata to Firestore persistence"""

    current_datetime = datetime.datetime.now()

    doc_ref = db.collection(config.GENMEDIA_COLLECTION_NAME).document()
    doc_ref.set(
        {
            "person_image_gcs": person_image_gcs,
            "product_image_gcs": product_image_gcs,
            "gcs_uris": result_image_gcs,
            "mime_type": "image/png",
            "user_email": user_email,
            "timestamp": current_datetime,
            "model": config.VTO_MODEL_ID,
        }
    )

    print(f"VTO data stored in Firestore with document ID: {doc_ref.id}")

def get_media_for_page(
    page: int,
    media_per_page: int,
    type_filters: Optional[List[str]] = None,
    error_filter: str = "all",  # "all", "no_errors", "only_errors"
    sort_by_timestamp: bool = False,
    filter_by_user_email: Optional[str] = None,  # New parameter
) -> List[MediaItem]:
    """Fetches a paginated and filtered list of media items from Firestore.

    NOTE: This implementation currently fetches a larger batch of items (up to 'fetch_limit')
    and then performs filtering and pagination client-side (in Python). For very large datasets
    in Firestore (e.g., many thousands of media items), this approach might become inefficient
    in terms of data transfer and memory usage. A more scalable long-term solution would involve
    server-side pagination and filtering directly using Firestore query cursors (`start_after`)
    and more complex `where` clauses if feasible, potentially via dedicated API endpoints.

    Args:
        page: The page number to fetch.
        media_per_page: The number of media items to fetch per page.
        type_filters: A list of media types to filter by.
        error_filter: The error filter to apply.

    Returns:
        A list of MediaItem objects.
    """
    fetch_limit = 1000  # Max items to fetch for client-side filtering/pagination

    try:
        query = db.collection(config.GENMEDIA_COLLECTION_NAME)

        if sort_by_timestamp:
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)

        all_fetched_items: List[MediaItem] = []
        for doc in query.limit(fetch_limit).stream():
            raw_item_data = doc.to_dict()
            if raw_item_data is None:
                print(f"Warning: doc.to_dict() returned None for doc ID: {doc.id}")
                continue

            mime_type = raw_item_data.get("mime_type", "")
            error_message_present = bool(raw_item_data.get("error_message"))

            # Apply type filters
            passes_type_filter = False
            if not type_filters or "all" in type_filters:
                passes_type_filter = True
            else:
                if "videos" in type_filters and mime_type.startswith("video/"):
                    passes_type_filter = True
                elif "images" in type_filters and mime_type.startswith("image/"):
                    passes_type_filter = True
                elif "music" in type_filters and mime_type.startswith("audio/"):
                    passes_type_filter = True

            if not passes_type_filter:
                continue

            # Apply error filter
            passes_error_filter = False
            if error_filter == "all":
                passes_error_filter = True
            elif error_filter == "no_errors" and not error_message_present:
                passes_error_filter = True
            elif error_filter == "only_errors" and error_message_present:
                passes_error_filter = True

            if not passes_error_filter:
                continue

            # Apply user email filter
            if filter_by_user_email and raw_item_data.get("user_email") != filter_by_user_email:
                continue

            # Construct MediaItem if all filters pass
            timestamp_iso_str: Optional[str] = None
            raw_timestamp = raw_item_data.get("timestamp")
            if isinstance(raw_timestamp, datetime.datetime):
                timestamp_iso_str = raw_timestamp.isoformat()
            elif isinstance(raw_timestamp, str):
                timestamp_iso_str = raw_timestamp  # Assuming it's already ISO format
            elif hasattr(raw_timestamp, "isoformat"):  # For Firestore Timestamp objects
                timestamp_iso_str = raw_timestamp.isoformat()

            # print(f"DEBUG: Fetched item with timestamp: {timestamp_iso_str}")

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
                aspect=str(raw_item_data.get("aspect"))
                if raw_item_data.get("aspect") is not None
                else None,
                gcsuri=str(raw_item_data.get("gcsuri"))
                if raw_item_data.get("gcsuri") is not None
                else None,
                gcs_uris=raw_item_data.get("gcs_uris", []),
                source_images_gcs=raw_item_data.get("source_images_gcs", []),
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
                negative_prompt=str(raw_item_data.get("negative_prompt"))
                if raw_item_data.get("negative_prompt") is not None
                else None,
                enhanced_prompt_used=raw_item_data.get("enhanced_prompt"),
                duration=item_duration,
                error_message=str(raw_item_data.get("error_message"))
                if raw_item_data.get("error_message") is not None
                else None,
                rewritten_prompt=str(raw_item_data.get("rewritten_prompt"))
                if raw_item_data.get("rewritten_prompt") is not None
                else None,
                comment=str(raw_item_data.get("comment"))
                if raw_item_data.get("comment") is not None
                else None,
                resolution=str(raw_item_data.get("resolution"))
                if raw_item_data.get("resolution") is not None
                else None,
                media_type=str(raw_item_data.get("media_type"))
                if raw_item_data.get("media_type") is not None
                else None,
                source_character_images=raw_item_data.get(
                    "source_character_images", []
                ),
                character_description=str(raw_item_data.get("character_description"))
                if raw_item_data.get("character_description") is not None
                else None,
                imagen_prompt=str(raw_item_data.get("imagen_prompt"))
                if raw_item_data.get("imagen_prompt") is not None
                else None,
                veo_prompt=str(raw_item_data.get("veo_prompt"))
                if raw_item_data.get("veo_prompt") is not None
                else None,
                candidate_images=raw_item_data.get("candidate_images", []),
                best_candidate_image=str(raw_item_data.get("best_candidate_image"))
                if raw_item_data.get("best_candidate_image") is not None
                else None,
                outpainted_image=str(raw_item_data.get("outpainted_image"))
                if raw_item_data.get("outpainted_image") is not None
                else None,
                raw_data=raw_item_data,
            )
            all_fetched_items.append(media_item)

        # For pagination, slice the fully filtered list
        start_slice = (page - 1) * media_per_page
        end_slice = start_slice + media_per_page
        return all_fetched_items[start_slice:end_slice]

    except Exception as e:
        print(f"Error fetching media from Firestore: {e}")
        # Optionally, you could re-raise or handle more gracefully
        return []


def get_media_for_page_optimized(
    page_size: int,
    type_filters: list[str],
    start_after=None,
):
    """
    Fetches a paginated and filtered list of media items from Firestore
    using server-side pagination and filtering.
    """
    try:
        query = db.collection(config.GENMEDIA_COLLECTION_NAME)

        # Apply type filters using WHERE clauses
        # Note: This requires Firestore indexes. For a single 'mime_type' startsWith,
        # a single-field index on 'mime_type' might suffice. For combinations with
        # sorting, a composite index is likely needed.
        if "videos" in type_filters:
            query = query.where("mime_type", ">=", "video/").where(
                "mime_type", "<", "video0"
            )
        elif "images" in type_filters:
            query = query.where("mime_type", ">=", "image/").where(
                "mime_type", "<", "image0"
            )
        elif "music" in type_filters:
            query = query.where("mime_type", ">=", "audio/").where(
                "mime_type", "<", "audio0"
            )

        # Always sort by timestamp
        query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)

        # Server-side pagination
        if start_after:
            query = query.start_after(start_after)

        query = query.limit(page_size)

        docs = list(query.stream())
        media_items = []
        for doc in docs:
            # This reuses the same parsing logic as the original function
            # A refactor could extract this parsing into a helper
            raw_item_data = doc.to_dict()
            if raw_item_data is None:
                continue

            timestamp_iso_str: Optional[str] = None
            raw_timestamp = raw_item_data.get("timestamp")
            if isinstance(raw_timestamp, datetime.datetime):
                timestamp_iso_str = raw_timestamp.isoformat()
            elif isinstance(raw_timestamp, str):
                timestamp_iso_str = raw_timestamp  # Assuming it's already ISO format
            elif hasattr(raw_timestamp, "isoformat"):  # For Firestore Timestamp objects
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
                aspect=str(raw_item_data.get("aspect"))
                if raw_item_data.get("aspect") is not None
                else None,
                gcsuri=str(raw_item_data.get("gcsuri"))
                if raw_item_data.get("gcsuri") is not None
                else None,
                gcs_uris=raw_item_data.get("gcs_uris", []),
                source_images_gcs=raw_item_data.get("source_images_gcs", []),
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
                negative_prompt=str(raw_item_data.get("negative_prompt"))
                if raw_item_data.get("negative_prompt") is not None
                else None,
                enhanced_prompt_used=raw_item_data.get("enhanced_prompt"),
                duration=item_duration,
                error_message=str(raw_item_data.get("error_message"))
                if raw_item_data.get("error_message") is not None
                else None,
                rewritten_prompt=str(raw_item_data.get("rewritten_prompt"))
                if raw_item_data.get("rewritten_prompt") is not None
                else None,
                comment=str(raw_item_data.get("comment"))
                if raw_item_data.get("comment") is not None
                else None,
                resolution=str(raw_item_data.get("resolution"))
                if raw_item_data.get("resolution") is not None
                else None,
                media_type=str(raw_item_data.get("media_type"))
                if raw_item_data.get("media_type") is not None
                else None,
                source_character_images=raw_item_data.get(
                    "source_character_images", []
                ),
                character_description=str(raw_item_data.get("character_description"))
                if raw_item_data.get("character_description") is not None
                else None,
                imagen_prompt=str(raw_item_data.get("imagen_prompt"))
                if raw_item_data.get("imagen_prompt") is not None
                else None,
                veo_prompt=str(raw_item_data.get("veo_prompt"))
                if raw_item_data.get("veo_prompt") is not None
                else None,
                candidate_images=raw_item_data.get("candidate_images", []),
                best_candidate_image=str(raw_item_data.get("best_candidate_image"))
                if raw_item_data.get("best_candidate_image") is not None
                else None,
                outpainted_image=str(raw_item_data.get("outpainted_image"))
                if raw_item_data.get("outpainted_image") is not None
                else None,
                raw_data=raw_item_data,
            )
            media_items.append(media_item)
        
        last_doc = docs[-1] if docs else None
        return media_items, last_doc

    except Exception as e:
        print(f"Error fetching media from Firestore (optimized): {e}")
        return [], None





