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

from pydantic import BaseModel, Field
from typing import List, Optional

class FacialCompositeProfile(BaseModel):
    """A detailed, structured representation of a person's facial features."""
    face_shape: str = Field(..., description="The overall shape of the face (e.g., oval, round, square).")
    eye_color: str = Field(..., description="The color of the eyes.")
    eye_shape: str = Field(..., description="The shape of the eyes (e.g., almond, round).")
    eyebrow_shape: str = Field(..., description="The shape and thickness of the eyebrows.")
    nose_shape: str = Field(..., description="The shape and size of the nose.")
    lip_shape: str = Field(..., description="The shape and fullness of the lips.")
    hair_color: str = Field(..., description="The color of the hair.")
    hair_style: str = Field(..., description="The style of the hair (e.g., short, long, curly, straight).")
    skin_tone: str = Field(..., description="The tone of the skin.")
    jawline: str = Field(..., description="The definition of the jawline (e.g., sharp, soft).")
    distinguishing_marks: Optional[List[str]] = Field(None, description="Any distinguishing marks like scars, moles, or tattoos.")

class GeneratedPrompts(BaseModel):
    """Holds the generated positive and negative prompts for image generation."""
    prompt: str = Field(..., description="The detailed, final prompt for the image generation model.")
    negative_prompt: str = Field(..., description="The negative prompt to guide the model away from undesirable attributes.")

class BestImage(BaseModel):
    """Pydantic model for the best image selection."""
    best_image_path: str
    reasoning: str

class WorkflowStepResult(BaseModel):
    """Represents the result of a single step in the workflow."""
    step_name: str
    status: str
    message: str
    duration_seconds: float
    data: dict
