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

import base64

import shortuuid
import vertexai
from google.api_core.exceptions import GoogleAPIError # Import GoogleAPIError
from google.cloud import aiplatform, storage

from config.default import Default

# Initialize Configuration
cfg = Default()
vertexai.init(project=cfg.PROJECT_ID, location=cfg.LOCATION)
aiplatform.init(project=cfg.PROJECT_ID, location=cfg.LOCATION)


def generate_music_with_lyria(prompt: str):
    """
    Generates music with Lyria and stores it in GCS.
    Raises:
        ValueError: If the Lyria API call fails, containing the error message from the API.
        Exception: For other unexpected errors during the process.
    """

    LOCATION = cfg.LOCATION
    MODEL_VERSION = cfg.LYRIA_MODEL_VERSION
    PROJECT_ID = cfg.LYRIA_PROJECT_ID # Ensure this is the correct project ID for Lyria model access
    LYRIA_ENDPOINT = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_VERSION}"

    # Initialize aiplatform within the function if it's specific to this call,
    # or ensure it's initialized globally if appropriate.
    # aiplatform.init(project=PROJECT_ID, location=LOCATION) # This might be redundant if already initialized globally

    instances = [{"prompt": prompt}] # Simplified instance creation
    parameters = {"sampleCount": 1}

    api_regional_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
    client_options = {"api_endpoint": api_regional_endpoint}
    # It's good practice to handle client creation within a try/except if it can fail
    try:
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    except Exception as client_err:
        print(f"Failed to create PredictionServiceClient: {client_err}")
        raise ValueError(f"Configuration error: Failed to initialize prediction client. Details: {str(client_err)}") from client_err


    print(
        f"Prediction client initiated on project {PROJECT_ID} in {LOCATION}: {LYRIA_ENDPOINT}."
    )

    destination_blob_name = None  # Initialize to None

    try:
        response = client.predict(
            endpoint=LYRIA_ENDPOINT,
            instances=instances,
            parameters=parameters,
        )
        
        # Check if predictions are present and valid
        if not response.predictions or not response.predictions[0].get("bytesBase64Encoded"):
            # Handle cases where the API might return a 200 OK but no valid prediction
            error_message = "Lyria API returned an unexpected response (no valid prediction data)."
            if response.predictions and response.predictions[0].get("error"): # Check for explicit error in payload
                 error_detail = response.predictions[0]["error"]
                 error_message = f"Lyria API Error: {error_detail.get('message', 'Unknown error from API payload')}"
            print(error_message)
            raise ValueError(error_message)

        contents = response.predictions[0]["bytesBase64Encoded"]

        # Create a file name
        my_uuid = shortuuid.uuid()
        file_name = f"lyria_generation_{my_uuid}.wav"

        # Store on GCS
        # This function call could also raise exceptions (e.g., GCS permissions, network issues)
        destination_blob_name = store_to_gcs(
            "music", file_name, "audio/wav", contents, True
        )

        print(
            f"{destination_blob_name} with contents len {len(contents)} uploaded to {cfg.MEDIA_BUCKET}."
        )

    except GoogleAPIError as e:
        # This catches errors from the client.predict call (e.g., 400, 500 from API)
        error_message = f"Lyria API Error: {str(e)}"
        print(error_message) # Log the detailed error
        # Raise a ValueError that the UI can catch and display directly.
        # The str(e) often contains the "400 Audio generation failed..." message.
        raise ValueError(error_message) from e
    except Exception as e:
        # Catch any other unexpected errors during the process (e.g., issues in store_to_gcs not caught there)
        error_message = f"An unexpected error occurred during music generation: {str(e)}"
        print(error_message)
        raise Exception(error_message) from e # Re-raise as a generic exception or a custom one

    # If destination_blob_name is still None here, it means an error occurred,
    # and an exception should have already been raised.
    # However, as a safeguard, though ideally the logic above ensures an error is raised.
    if destination_blob_name is None:
        # This case should ideally not be reached if error handling above is complete.
        raise Exception("Music generation failed, and no specific error was propagated.")

    return destination_blob_name


def store_to_gcs(
    folder: str, file_name: str, mime_type: str, contents: str, decode: bool = False
):
    """
    Stores contents to GCS.
    Raises:
        ValueError: If GCS client cannot be initialized or bucket is not found.
        GoogleAPIError: For GCS API errors during upload.
        Exception: For other unexpected errors.
    """
    try:
        client = storage.Client(project=cfg.PROJECT_ID)
        bucket = client.get_bucket(cfg.MEDIA_BUCKET)
    except Exception as e:
        # Handle errors in initializing client or getting bucket
        error_message = f"Failed to initialize GCS client or access bucket '{cfg.MEDIA_BUCKET}': {str(e)}"
        print(error_message)
        raise ValueError(error_message) from e # Raise a more specific error for config/permission issues

    destination_blob_name = f"{folder}/{file_name}"
    blob = bucket.blob(destination_blob_name)
    
    try:
        if decode:
            contents_bytes = base64.b64decode(contents) # This can raise binascii.Error if contents are not valid base64
            blob.upload_from_string(contents_bytes, content_type=mime_type)
        else:
            blob.upload_from_string(contents, content_type=mime_type)
    except base64.binascii.Error as b64_err: # More specific error for base64 decoding
        error_message = f"Failed to decode base64 content for GCS upload ({file_name}): {str(b64_err)}"
        print(error_message)
        raise ValueError(error_message) from b64_err
    except GoogleAPIError as gcs_api_err: # Catch GCS specific API errors
        error_message = f"GCS API error during upload of {file_name}: {str(gcs_api_err)}"
        print(error_message)
        raise # Re-raise the GCS API error to be potentially handled upstream or logged with its specific type
    except Exception as e:
        # Catch other unexpected errors during upload
        error_message = f"Unexpected error during GCS upload of {file_name}: {str(e)}"
        print(error_message)
        raise Exception(error_message) from e

    return f"{cfg.MEDIA_BUCKET}/{destination_blob_name}"

