# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import base64
import io
import json
import re
from typing import Any
import datetime

from absl import logging
from PIL import Image
import google.auth
from google.cloud import storage
from google.auth import impersonated_credentials

import os

from config.default import Default as cfg


def create_display_url(gcs_uri: str) -> str:
    """
    Creates a cacheable display URL for a GCS asset.
    Switches between a direct GCS link and the app proxy based on config.
    """
    if not gcs_uri or not gcs_uri.startswith("gs://"):
        return ""

    if cfg().USE_MEDIA_PROXY:
        # Use the fast, simple proxy URL
        proxy_path = gcs_uri.replace("gs://", "")
        return f"/media/{proxy_path}"
    else:
        # Use the direct GCS URL
        return gcs_uri.replace("gs://", "https://storage.cloud.google.com/")




def extract_username(email_string: str | None) -> str:
    """Extracts the username from an email-like string.

    Args:
        email_string: The string containing the username and domain.

    Returns:
        The extracted username, or None if no valid username is found.
    """
    if email_string:
        match = re.search(
            r":([^@]+)@", email_string
        )  # Matches anything between ":" and "@"
        if match:
            return match.group(1)
    return "Anonymous"


def get_image_dimensions_from_base64(base64_string: str) -> tuple[int, int]:
    """Retrieves the width and height of an image from a base64 encoded string.

    Args:
        base64_string: The base64 encoded image data.

    Returns:
        A tuple (width, height) if successful, or None if an error occurs.
    """
    try:
        # Remove the data URL prefix if it exists.
        if base64_string.startswith("data:image"):
            parts = base64_string.split(",")
            if len(parts) > 1:
                base64_string = parts[1]

        image_data = base64.b64decode(base64_string)
        image_stream = io.BytesIO(image_data)
        img = Image.open(image_stream)
        width, height = img.size
        return width, height
    except Exception as e:
        logging.info(f"App: Error getting image dimensions: {e}")
        return None


def make_local_request(endpoint: str) -> dict[str, Any]:
    filepath = (
        f"mocks/{endpoint}.json"  # Assuming mock files are in a 'mocks' directory
    )
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        logging.info(f"Mock file not found: {filepath}")
        return None  # Or raise an exception
    
    
def print_keys(obj, prefix=""):
    """Recursively prints keys of a JSON object."""
    if obj is None:  # Base case: if obj is None, do nothing and return
        return
    if isinstance(obj, dict):
        for key in obj:
            print(prefix + key)
            print_keys(obj[key], prefix + "  ")  # Recurse with increased indentation
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            # For lists, we might want to indicate the index and then recurse on the item
            # If the item itself is a complex object.
            # If you only want to print keys of dicts within a list,
            # you might adjust the print statement here or what you pass to print_keys.
            # Current behavior: treats list items as potentially new objects to explore.
            print_keys(item, prefix + f"  [{i}] ")  # indicate list index in prefix

GCS_PUBLIC_URL_PREFIX = "https://storage.cloud.google.com/"

def _get_gcs_public_https_url(gcs_uri: str | None) -> str:
    """
    (Internal use only) Converts a GCS URI to a publicly accessible URL.
    This performs a simple string replacement and does NOT work for private objects.
    """
    if not gcs_uri:
        return ""
    if gcs_uri.startswith("https://"):
        return gcs_uri
    if gcs_uri.startswith("gs://"):
        return gcs_uri.replace("gs://", GCS_PUBLIC_URL_PREFIX)
    # Return as-is if it's not a recognized format
    return gcs_uri

def https_url_to_gcs_uri(url: str | None) -> str:
    """
    Converts a public GCS HTTPS URL (including signed URLs) back to a gs:// URI.
    """
    if not url:
        return ""
    if url.startswith("gs://"):
        return url

    # Handle local media proxy URLs
    if url.startswith("/media/"):
        return f"gs://{url.replace('/media/', '')}"

    # Take the base URL, stripping any query parameters from a signed URL
    url_to_convert = url.split("?")[0]

    if url_to_convert.startswith("https://storage.googleapis.com/"):
        return url_to_convert.replace("https://storage.googleapis.com/", "gs://")
    if url_to_convert.startswith(GCS_PUBLIC_URL_PREFIX):
        return url_to_convert.replace(GCS_PUBLIC_URL_PREFIX, "gs://")

    # If it's not a recognized GCS URL, return the original input as a fallback.
    return url


def get_media_type(mime_type: str | None = None, url: str | None = None) -> str:
    """Determines the media type (image, video, audio) based on mime_type or URL."""
    if mime_type:
        if mime_type.startswith("video/"):
            return "video"
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("audio/"):
            return "audio"

    if url:
        url_lower = url.lower()
        if any(ext in url_lower for ext in [".mp4", ".webm", ".mov"]):
            return "video"
        if any(ext in url_lower for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
            return "image"
        if any(ext in url_lower for ext in [".wav", ".mp3", ".ogg"]):
            return "audio"

    return "image"  # Default fallback
