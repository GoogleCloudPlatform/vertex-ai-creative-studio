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

import json

import mesop as me

from common.analytics import log_page_view
from components.welcome_hero.welcome_hero import welcome_hero
from state.state import AppState


@me.stateclass
class PageState:
    pass


def on_tile_click(e: me.WebEvent):
    route = e.value["route"]
    me.navigate(route)
    yield


@me.page(
    path="/welcome",
    title="Welcome - GenMedia Creative Studio",
)
def page():
    """Define the Mesop page route for the welcome page."""
    app_state = me.state(AppState)
    log_page_view(page_name="welcome", session_id=app_state.session_id)

    tiles_data = [
        {"icon": "home", "route": "/home"},
        {"label": "Veo", "route": "/veo"},
        {"label": "Gemini Image Generation", "icon": "banana", "route": "/gemini_image_generation"},
        {"label": "Lyria", "route": "/lyria"},
        {"label": "Speech", "route": "/home"},
        {"label": "Workflows", "route": "/home"},
    ]

    welcome_hero(
        title="GenMedia Creative Studio",
        subtitle="Fuel your creativity with Google Cloud Vertex AI's generative media models and custom workflows.",
        video_url="https://deepmind.google/api/blob/website/media/veo__cover_s0RKXWX.mp4",
        tiles=json.dumps(tiles_data),
        on_tile_click=on_tile_click,
    )
