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

from absl import logging
from PIL import Image


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


def gcs_uri_to_https_url(gcs_uri: str | None) -> str:
    """
    Converts a GCS URI to a publicly accessible URL via the proxy endpoint.

    Handles None, empty strings, and already-formatted URLs gracefully.
    """
    if not gcs_uri:
        return ""
    if gcs_uri.startswith("https://") and not gcs_uri.startswith(GCS_PUBLIC_URL_PREFIX):
        return gcs_uri
    if gcs_uri.startswith("gs://") or gcs_uri.startswith(GCS_PUBLIC_URL_PREFIX):
        # Convert to gs:// format if it's a direct GCS URL
        gs_uri = gcs_uri if gcs_uri.startswith("gs://") else gcs_uri.replace(GCS_PUBLIC_URL_PREFIX, "gs://")
        # Use the proxy endpoint to serve the content with proper authentication
        from urllib.parse import quote
        return f"/api/get_signed_url_proxy?gcs_uri={quote(gs_uri)}"
    # Return as-is if it's not a recognized format
    return gcs_uri


def proxy_url_to_gcs_uri(proxy_url: str | None) -> str:
    """
    Converts a proxy URL back to a gs:// URI.
    """
    if not proxy_url:
        return ""
    if proxy_url.startswith("/api/get_signed_url_proxy?gcs_uri="):
        from urllib.parse import unquote
        # Extract the gcs_uri parameter from the proxy URL
        gcs_uri_param = proxy_url.split("gcs_uri=")[1]
        return unquote(gcs_uri_param)
    return proxy_url


def https_url_to_gcs_uri(url: str | None) -> str:
    """
    Converts a public GCS HTTPS URL back to a gs:// URI.
    """
    if not url:
        return ""
    if url.startswith("gs://"):
        return url
    if url.startswith(GCS_PUBLIC_URL_PREFIX):
        return url.replace(GCS_PUBLIC_URL_PREFIX, "gs://")
    return url
