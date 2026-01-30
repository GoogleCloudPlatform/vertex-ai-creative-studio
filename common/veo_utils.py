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

import logging
import requests
from common.analytics import track_model_call
from config.default import Default
from config.veo_models import get_veo_model_config
from models.requests import VideoGenerationRequest

logger = logging.getLogger(__name__)
config = Default()

def start_async_veo_job(
    request: VideoGenerationRequest,
    user_email: str,
    mode: str = "t2v"
) -> dict:
    """
    Initiates an asynchronous Veo generation job via the API.
    Handles analytics logging and API error checking.

    Args:
        request: The generation request object.
        user_email: The email of the user initiating the request.
        mode: The operation mode (e.g., 't2v', 'i2v', 'extension').

    Returns:
        A dictionary containing the job response (e.g., {'job_id': '...', 'status': '...'}).

    Raises:
        Exception: If the API call fails.
    """
    api_url = f"{config.API_BASE_URL}/api/veo/generate_async"
    headers = {"X-Goog-Authenticated-User-Email": user_email}
    
    # Determine model name for analytics
    model_config = get_veo_model_config(request.model_version_id)
    model_name_for_analytics = model_config.model_name if model_config else request.model_version_id

    try:
        with track_model_call(
            model_name=model_name_for_analytics,
            prompt_length=len(request.prompt) if request.prompt else 0,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
            video_count=request.video_count,
            mode=mode,
        ):
            request_json = request.model_dump()
            logger.info(f"Starting Veo Job. Request: {request_json}")
            response = requests.post(api_url, json=request_json, headers=headers)
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Failed to start Veo job: {e}")
        raise e
