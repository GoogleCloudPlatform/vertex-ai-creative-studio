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

"""This module provides a class for setting up the generative AI model.

It includes a class with a static method to initialize the `genai` client with
the appropriate project ID, location, and model ID.
"""

from typing import Optional
from dotenv import load_dotenv
from google import genai
from config.default import Default


load_dotenv(override=True)


class ModelSetup:
    """A class to handle the setup of the generative AI model."""

    @staticmethod
    def init(
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_id: Optional[str] = None,
        planning_model_id: Optional[str] = None,
    ):
        """Initializes the generative AI client.

        This static method sets up the `genai` client with the specified project
        ID, location, and model ID. If these parameters are not provided, it
        falls back to the values in the default configuration.

        Args:
            project_id: The Google Cloud project ID.
            location: The Google Cloud location to use for the model.
            model_id: The ID of the model to use.
            planning_model_id: The ID of the model to use for planning.

        Returns:
            A tuple containing the initialized `genai` client, the model ID, and the planning model ID.

        Raises:
            ValueError: If any of the required parameters are not set.
        """
        config = Default()
        if not project_id:
            project_id = config.PROJECT_ID
        if not location:
            location = config.LOCATION
        if not model_id:
            model_id = config.MODEL_ID
        if not planning_model_id:
            planning_model_id = config.PLANNING_MODEL_ID or model_id

        if None in [project_id, location, model_id]:
            raise ValueError("All parameters must be set.")
        print(f"initiating genai client with {project_id} in {location}")
        client = genai.Client(
            vertexai=config.INIT_VERTEX,
            project=project_id,
            location=location,
        )
        return client, model_id, planning_model_id
