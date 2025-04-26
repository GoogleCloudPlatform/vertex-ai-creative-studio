from typing import Optional
from dotenv import load_dotenv
from google import genai
from config.default import Default

import vertexai


load_dotenv(override=True)


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

        #return video_model, prediction_endpoint, fetch_endpoint


class GeminiModelSetup:
    """Gemini model setup"""
    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """Init method"""
        config = Default()
        if not project_id:
            project_id = config.PROJECT_ID
        if not location:
            location = config.LOCATION
        if not model_id:
            model_id = config.MODEL_ID
        if None in [project_id, location, model_id]:
            raise ValueError("All parameters must be set.")
        print(f"initiating genai client with {project_id} in {location}")
        client = genai.Client(
            vertexai=config.INIT_VERTEX,
            project=project_id,
            location=location,
        )
        return client, model_id
