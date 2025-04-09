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

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

import mesop as me

from google import genai
from google.genai.types import (
    GenerateContentConfig,
)

from components.header import header

from models.set_up import ModelSetup

client, model_id = ModelSetup.init()
MODEL_ID = model_id


@retry(
    wait=wait_exponential(
        multiplier=1, min=1, max=10
    ),  # Exponential backoff (1s, 2s, 4s... up to 10s)
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    retry=retry_if_exception_type(Exception),  # Retry on all exceptions
    reraise=True,  # re-raise the last exception if all retries fail
)
def say_something_nice(name: str) -> str:
    """Says something nice about a given name using Gemini."""
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=f"say something nice about {name}, they're testing you, gemini 2.0, and you appreciate this! please make it a few sentences. You may address them by name.",
            config=GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )
        print(f"success! {response.text}")
        return response.text
    except Exception as e:
        print(f"error: {e}")
        raise  # Re-raise the exception for tenacity to handle


def gemini_page_content(app_state: me.state):
    """Gemini 2.0 Flash Mesop Page"""

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            height="100%",
        ),
    ):
        with me.box(
            style=me.Style(
                background=me.theme_var("background"),
                height="100%",
                overflow_y="scroll",
                margin=me.Margin(bottom=20),
            )
        ):
            with me.box(
                style=me.Style(
                    background=me.theme_var("background"),
                    padding=me.Padding(top=24, left=24, right=24, bottom=24),
                    display="flex",
                    flex_direction="column",
                )
            ):
                header("Gemini 2.0 Flash", "auto_awesome")

                me.text(f"Hello, {app_state.name}!")

                me.box(style=me.Style(height=16))

                me.text(say_something_nice(app_state.name))
