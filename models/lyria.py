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
from google.cloud import aiplatform # storage import removed
# from google.cloud import storage # No longer needed here

from config.default import Default
from common.storage import store_to_gcs # Import the common function

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

    MODEL_VERSION = cfg.LYRIA_MODEL_VERSION
    PROJECT_ID = cfg.LYRIA_PROJECT_ID
    # The model resource path uses 'global'
    LYRIA_ENDPOINT = f"projects/{PROJECT_ID}/locations/global/publishers/google/models/{MODEL_VERSION}"

    # The serving endpoint is defined by the new config variable
    api_regional_endpoint = f"{cfg.LYRIA_LOCATION}-aiplatform.googleapis.com"
    client_options = {"api_endpoint": api_regional_endpoint}
    # It's good practice to handle client creation within a try/except if it can fail
    try:
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    except Exception as client_err:
        print(f"Failed to create PredictionServiceClient: {client_err}")
        raise ValueError(f"Configuration error: Failed to initialize prediction client. Details: {str(client_err)}") from client_err


    print(
        f"Prediction client initiated on project {PROJECT_ID} in {cfg.LYRIA_LOCATION}: {LYRIA_ENDPOINT}."
    )

    destination_blob_name = None  # Initialize to None

    instances = [{"prompt": prompt}]
    parameters = {"sampleCount": 1}

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
            "music", file_name, "audio/wav", contents, True, bucket_name=cfg.MEDIA_BUCKET
        )

        print(
            f"{destination_blob_name} with contents len {len(contents)} uploaded (intended for {cfg.MEDIA_BUCKET})."
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