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


import json
import urllib.error
import urllib.request

import google.auth
import google.auth.transport.requests
import shortuuid
import vertexai
from google.api_core.exceptions import GoogleAPIError  # Import GoogleAPIError
from google.cloud import aiplatform  # storage import removed

from common.analytics import get_logger, track_model_call
from common.storage import store_to_gcs  # Import the common function

# from google.cloud import storage # No longer needed here
from config.default import Default

logger = get_logger(__name__)

# Initialize Configuration
cfg = Default()
vertexai.init(project=cfg.PROJECT_ID, location=cfg.LOCATION)
aiplatform.init(project=cfg.PROJECT_ID, location=cfg.LOCATION)


def generate_music_with_lyria(
    prompt: str,
    model_name: str = "lyria-002",
    lyrics: str = None,
    image_gcs_uri: str = None,
    image_b64: str = None,
    image_mime_type: str = "image/jpeg",
    sample_count: int = 1,
):
    """Generates music with Lyria and stores it in GCS.

    Raises:
        ValueError: If the Lyria API call fails, containing the error message from the API.
        Exception: For other unexpected errors during the process.

    """
    billing_units = {
        "sample_count": sample_count,
        "has_lyrics": bool(lyrics),
        "has_image_conditioning": bool(image_gcs_uri or image_b64),
    }

    with track_model_call(model_name, billing_units=billing_units) as ctx:
        if "lyria-002" in model_name:
            MODEL_VERSION = cfg.LYRIA_MODEL_VERSION
            PROJECT_ID = cfg.LYRIA_PROJECT_ID
            LYRIA_ENDPOINT = f"projects/{PROJECT_ID}/locations/global/publishers/google/models/{MODEL_VERSION}"

            api_regional_endpoint = f"{cfg.LYRIA_LOCATION}-aiplatform.googleapis.com"
            client_options = {"api_endpoint": api_regional_endpoint}
            try:
                client = aiplatform.gapic.PredictionServiceClient(
                    client_options=client_options,
                )
            except Exception as client_err:
                logger.error(f"Failed to create PredictionServiceClient: {client_err}")
                raise ValueError(
                    f"Configuration error: Failed to initialize prediction client. Details: {client_err!s}",
                ) from client_err

            logger.info(
                f"Prediction client initiated on project {PROJECT_ID} in {cfg.LYRIA_LOCATION}: {LYRIA_ENDPOINT}. Requesting {sample_count} samples.",
            )

            instances = [{"prompt": prompt}]
            parameters = {"sampleCount": sample_count}

            try:
                response = client.predict(
                    endpoint=LYRIA_ENDPOINT,
                    instances=instances,
                    parameters=parameters,
                )

                if not response.predictions or not response.predictions[0].get(
                    "bytesBase64Encoded",
                ):
                    error_message = "Lyria API returned an unexpected response (no valid prediction data)."
                    if response.predictions and response.predictions[0].get("error"):
                        error_detail = response.predictions[0]["error"]
                        error_message = f"Lyria API Error: {error_detail.get('message', 'Unknown error from API payload')}"
                    logger.error(error_message)
                    raise ValueError(error_message)

                destination_blob_names = []
                for prediction in response.predictions:
                    contents = prediction["bytesBase64Encoded"]
                    my_uuid = shortuuid.uuid()
                    file_name = f"lyria_generation_{my_uuid}.wav"

                    destination_blob_name = store_to_gcs(
                        "music",
                        file_name,
                        "audio/wav",
                        contents,
                        True,
                        bucket_name=cfg.MEDIA_BUCKET,
                    )
                    destination_blob_names.append(destination_blob_name)

                ctx["billing_units"]["sample_count"] = len(destination_blob_names)
                logger.info(f"{len(destination_blob_names)} audio clips uploaded.")
                return destination_blob_names, None, []

            except GoogleAPIError as e:
                error_message = f"Lyria API Error: {e!s}"
                logger.error(error_message)
                raise ValueError(error_message) from e
            except Exception as e:
                error_message = (
                    f"An unexpected error occurred during music generation: {e!s}"
                )
                logger.error(error_message)
                raise Exception(error_message) from e

        # Lyria 3 logic via REST
        credentials, project_id = google.auth.default()
        if not credentials.valid:
            credentials.refresh(google.auth.transport.requests.Request())

        location = cfg.LYRIA_LOCATION
        if not location or location == "global":
            location = "us-central1"  # Or any valid fallback, but the API endpoint in test uses global

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{cfg.PROJECT_ID}/locations/global/interactions"

        inputs = []
        if prompt:
            inputs.append({"type": "text", "text": prompt})
        if lyrics:
            inputs.append({"type": "text", "text": f"With the lyrics: {lyrics}"})
        if image_gcs_uri:
            inputs.append(
                {"type": "image", "mime_type": image_mime_type, "uri": image_gcs_uri},
            )
        elif image_b64:
            inputs.append(
                {"type": "image", "mime_type": image_mime_type, "data": image_b64},
            )

        payload = {"model": model_name, "input": inputs}

        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        logger.info(f"Sending POST request to: {url}")

        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                body = response.read()
                logger.info(f"SUCCESS: Status {status}")

                resp_json = json.loads(body.decode("utf-8"))
                audio_b64 = None
                c2pa_data = None
                text_outputs = []
                if "outputs" in resp_json:
                    for o in resp_json["outputs"]:
                        if o.get("type") == "audio":
                            audio_b64 = o.get("data")
                        elif o.get("type") == "content_credentials":
                            c2pa_data = o.get("data")
                        elif o.get("type") == "text":
                            text_val = o.get("text")
                            if text_val:
                                text_outputs.append(text_val)

                if not audio_b64:
                    raise ValueError(
                        "Lyria API returned an unexpected response (no valid prediction data).",
                    )

                destination_blob_names = []
                contents = audio_b64
                my_uuid = shortuuid.uuid()
                file_name = f"lyria_generation_{my_uuid}.wav"

                destination_blob_name = store_to_gcs(
                    "music",
                    file_name,
                    "audio/wav",
                    contents,
                    True,
                    bucket_name=cfg.MEDIA_BUCKET,
                )
                destination_blob_names.append(destination_blob_name)
                logger.info(f"{destination_blob_name} uploaded.")
                return destination_blob_names, c2pa_data, text_outputs

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            error_message = f"Lyria API HTTP Error: {e.code} - {body}"
            logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            error_message = (
                f"An unexpected error occurred during music generation: {e!s}"
            )
            logger.error(error_message)
            raise Exception(error_message)
