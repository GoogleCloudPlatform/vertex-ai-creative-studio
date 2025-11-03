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

"""A reusable button for navigating to the Veo page."""

import mesop as me

from common.analytics import log_ui_click
from state.state import AppState

def on_send_to_veo(e: me.ClickEvent):
    """Navigates to the Veo page with the selected image as a query parameter."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="veo_button",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
    )
    gcs_uri = e.key
    me.navigate(
        url="/veo",
        query_params={"image_uri": gcs_uri, "veo_model": "3.0-fast"},
    )
    yield

@me.component
def veo_button(gcs_uri: str):
    """
    A reusable button that navigates to the Veo page with the provided
    image GCS URI.

    Args:
        gcs_uri: The Google Cloud Storage URI of the image to send to Veo.
    """
    with (
        me.content_button(
            on_click=on_send_to_veo,
            key=gcs_uri,
        ),
        me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                align_items="center",
                gap=8,
            )
        ),
    ):
        me.icon("slideshow")
        me.text("Veo")
