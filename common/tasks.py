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
"""Utility for enqueuing Cloud Tasks."""

import json
import logging
import os

from google.cloud import tasks_v2

from config.default import Default as cfg

logger = logging.getLogger(__name__)


def enqueue_thumbnail_task(job_id: str, video_uri: str) -> bool:
    """Enqueues a Cloud Task to generate a thumbnail for a video.

    Falls back to logging if Cloud Tasks is not configured.
    """
    project = cfg().PROJECT_ID
    queue = os.environ.get("THUMBNAIL_QUEUE_ID")
    location = cfg().LOCATION
    url = f"{cfg().API_BASE_URL}/api/veo/thumbnail"

    if not queue:
        logger.warning("THUMBNAIL_QUEUE_ID not set. Skipping Cloud Task enqueue.")
        return False

    try:
        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(project, location, queue)

        payload = {
            "job_id": job_id,
            "video_uri": video_uri,
        }

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {"Content-type": "application/json"},
                "body": json.dumps(payload).encode(),
            },
        }

        # Add OIDC token for authentication if running on Cloud Run
        if os.environ.get("K_SERVICE"):
            task["http_request"]["oidc_token"] = {
                "service_account_email": cfg().SERVICE_ACCOUNT_EMAIL,
            }

        response = client.create_task(request={"parent": parent, "task": task})
        logger.info(f"Created Cloud Task: {response.name}")
        return True
    except Exception:
        logger.exception(f"Failed to enqueue Cloud Task for job {job_id}")
        return False
