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

from pydantic import BaseModel, Field


class VideoGenerationRequest(BaseModel):
    """
    Defines the contract for a video generation request.
    This schema is used by the UI to call the model layer and will be
    the schema for the future FastAPI endpoint.
    """

    prompt: str
    duration_seconds: int = Field(..., gt=0)
    aspect_ratio: str
    resolution: str
    enhance_prompt: bool
    model_version_id: str
    person_generation: str
    negative_prompt: Optional[str] = None
    reference_image_gcs: Optional[str] = None
    last_reference_image_gcs: Optional[str] = None
    reference_image_mime_type: Optional[str] = None
    last_reference_image_mime_type: Optional[str] = None
