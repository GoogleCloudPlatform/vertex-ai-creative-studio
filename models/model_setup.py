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

from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.cloud import aiplatform

from config.default import Default

import vertexai


load_dotenv(override=True)


class VtoModelSetup:
    """Vto Model Setup"""

    def __init__(
        self: object,
    ) -> None:
        self._video_model = None
        self._prediction_endpoint = None
        self._fetch_endpoint = None

    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """initializes vto model"""

        config = Default()

        if not project_id:
            project_id = config.VEO_PROJECT_ID
        if not location:
            location = config.LOCATION
        if not model_id:
            model_id = config.VTO_MODEL_ID
        if None in [project_id, location, model_id]:
            raise ValueError("All parameters must be set.")

        vertexai.init(project=project_id, location=Default.LOCATION)

        aiplatform.init(project=f"{project_id}", location=f"{location}")
        api_regional_endpoint = f"{location}-aiplatform.googleapis.com"
        client_options = {"api_endpoint": api_regional_endpoint}
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
        # model_endpoint = f"projects/{project_id}/locations/{location}/publishers/google/models/virtual-try-on-exp-05-31"
        model_endpoint = f"projects/{project_id}/locations/{location}/publishers/google/models/{model_id}"
        print(f"Prediction client initiated on project {project_id} in {location}.")

        return client, model_endpoint


class VeoModelSetup:
    """Veo Model Setup"""

    def __init__(
        self: object,
    ) -> None:
        self._video_model = None
        self._prediction_endpoint = None
        self._fetch_endpoint = None

    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """initializes veo model"""

        config = Default()
        if not project_id:
            project_id = config.VEO_PROJECT_ID
        if not location:
            location = config.LOCATION
        if not model_id:
            model_id = config.VEO_MODEL_ID
        if None in [project_id, location, model_id]:
            raise ValueError("All parameters must be set.")
        vertexai.init(project=project_id, location=Default.LOCATION)

        # _video_model = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/us-central1/publishers/google/models/{model_id}"
        # self._prediction_endpoint = f"{self._video_model}:predictLongRunning"
        # self._fetch_endpoint = f"{self._video_model}:fetchPredictOperation"

        return model_id


class GeminiModelSetup:
    """Gemini model setup"""

    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        # model_id is no longer used by init, client is configured generally
    ):
        """Init method for Gemini client. Model is specified at call time."""
        config = Default()
        effective_project_id = project_id if project_id else config.PROJECT_ID
        effective_location = location if location else config.LOCATION

        if not effective_project_id or not effective_location:
            raise ValueError("Project ID and Location must be set for Gemini client.")

        print(
            f"Initiating Gemini client for project {effective_project_id} in {effective_location}"
        )
        client = genai.Client(
            vertexai=config.INIT_VERTEX,  # This assumes vertexai backend is desired.
            project=effective_project_id,
            location=effective_location,
        )
        return client
