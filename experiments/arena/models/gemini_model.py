# Copyright 2024 Google LLC
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
""" Gemini model methods """

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

from google import genai
from google.genai.types import (
    GenerateContentConfig,
)
from google.genai.errors import ClientError
import vertexai

from models.set_up import ModelSetup


# Initialize configuration
client, model_id = ModelSetup.init()
MODEL_ID = model_id


@retry(
    wait=wait_exponential(
        multiplier=2, min=1, max=25
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions
    reraise=True,  # re-raise the last exception if all retries fail
)
def generate_images(prompt: str) -> list[str]:
    """generate image content"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        print(f"success! {response.candidates[0].content}")
        return [res.text for res in response.candidates]

    except Exception as e:
        print(f"error: {e}")
        raise  # Re-raise the exception for tenacity to handle


@retry(
    wait=wait_exponential(
        multiplier=2, min=1, max=25
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions
    reraise=True,  # re-raise the last exception if all retries fail
)
def generate_content(prompt: str) -> str:
    """generate text content"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )
        print(f"success! {response.text}")
        return response.text

    except Exception as e:
        print(f"error: {e}")
        raise  # Re-raise the exception for tenacity to handle
