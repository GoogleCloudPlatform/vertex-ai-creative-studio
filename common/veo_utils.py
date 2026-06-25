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
"""Utilities for interacting with Veo services from Mesop pages."""

import logging
import threading

from common.analytics import track_model_call
from config.default import Default
from config.veo_models import get_veo_model_config
from models.requests import VideoGenerationRequest
from services.veo_service import create_initial_job, process_veo_generation_task

logger = logging.getLogger(__name__)
config = Default()


def start_async_veo_job(
    request: VideoGenerationRequest, user_email: str, mode: str = "t2v"
) -> dict:
    """Initiates an asynchronous Veo generation job by calling the service directly.

    Args:
        request: The generation request object.
        user_email: The email of the user initiating the request.
        mode: The operation mode (e.g., 't2v', 'i2v', 'extension').

    Returns:
        A dictionary containing the job response: {'job_id': '...', 'status': '...'}.
    """
    # Determine model name for analytics
    model_config = get_veo_model_config(request.model_version_id)
    model_name_for_analytics = (
        model_config.model_name if model_config else request.model_version_id
    )

    try:
        with track_model_call(
            model_name=model_name_for_analytics,
            prompt_length=len(request.prompt) if request.prompt else 0,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
            video_count=request.video_count,
            mode=mode,
        ):
            # 1. Create the job record in Firestore immediately
            job_id = create_initial_job(request, user_email)

            # 2. Start the background generation task in a separate thread.
            # This mimics the behavior of FastAPI's BackgroundTasks but works
            # directly within the Mesop process without an HTTP call.
            threading.Thread(
                target=process_veo_generation_task,
                args=(job_id, request, user_email),
                daemon=True,
            ).start()

            return {"job_id": job_id, "status": "pending"}

    except Exception:
        logger.exception(f"Failed to start Veo job for user {user_email}")
        raise
