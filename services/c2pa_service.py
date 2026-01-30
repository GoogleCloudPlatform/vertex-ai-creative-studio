# Copyright 2025 Google LLC
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

"""Service for reading C2PA manifests from images."""

import json
import os
import tempfile
import c2pa
from common.storage import download_from_gcs
from common.analytics import analytics_logger

class C2PAService:
    """Service to handle C2PA operations."""

    def read_manifest(self, image_uri: str) -> dict | None:
        """
        Reads the C2PA manifest from a local file or GCS URI.

        Args:
            image_uri: Local path or gs:// URI to the image.

        Returns:
            The manifest store as a dictionary, or None if no manifest found or error.
        """
        local_path = image_uri
        is_temp = False

        try:
            # Handle GCS URIs
            if image_uri.startswith("gs://"):
                # Create a temporary file to download the image
                fd, local_path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                is_temp = True
                
                # Download content (bytes) and write to temp file
                # We use download_from_gcs which returns bytes
                image_bytes = download_from_gcs(image_uri)
                with open(local_path, "wb") as f:
                    f.write(image_bytes)

            # Validate file exists
            if not os.path.exists(local_path):
                analytics_logger.warning(f"C2PA: File not found at {local_path}")
                return None

            # Read C2PA data
            try:
                with c2pa.Reader(local_path) as reader:
                    manifest_json = reader.json()
                    if not manifest_json:
                        return None
                    return json.loads(manifest_json)
            except c2pa.Error.ManifestNotFound:
                # This is expected for images without credentials
                return None
            except Exception as e:
                analytics_logger.error(f"C2PA Reader error for {image_uri}: {e}")
                return None

        except Exception as e:
            analytics_logger.error(f"C2PA Service unexpected error: {e}")
            return None
        finally:
            # Cleanup temp file if we created one
            if is_temp and os.path.exists(local_path):
                os.remove(local_path)

# Global instance
c2pa_service = C2PAService()
