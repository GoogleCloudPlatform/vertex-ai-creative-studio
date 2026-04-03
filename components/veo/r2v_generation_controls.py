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

import mesop as me

from config.veo_models import get_veo_model_config, get_models_by_mode
from state.veo_and_me_state import PageState


@me.component
def r2v_generation_controls(on_selection_change_veo_model):
    """Focused generation controls for the R2V page."""
    state = me.state(PageState)
    selected_config = get_veo_model_config(state.veo_model)

    if not selected_config:
        return

    # Define the specific models available on this page
    r2v_models = [model.version_id for model in get_models_by_mode("r2v")]
    model_options = [
        me.SelectOption(label=get_veo_model_config(v).display_name, value=v) for v in r2v_models
    ]

    with me.box(style=me.Style(display="flex", flex_direction="row", gap=10)):
        # Model selection (enabled for specific models)
        me.select(
            label="Model",
            appearance="outline",
            options=model_options,
            value=state.veo_model,
            on_selection_change=on_selection_change_veo_model,
        )

        # Number of videos
        me.select(
            label="count",
            appearance="outline",
            options=[
                me.SelectOption(label=str(i), value=str(i))
                for i in range(1, selected_config.max_samples + 1)
            ],
            value=str(state.video_count),
            style=me.Style(width="100px"),
        )

        # Aspect ratio (disabled)
        me.select(
            label="Aspect Ratio",
            appearance="outline",
            options=[
                me.SelectOption(label=ratio, value=ratio)
                for ratio in selected_config.supported_aspect_ratios
            ],
            value=state.aspect_ratio,
            disabled=True,
        )

        # Resolution
        me.select(
            label="Resolution",
            appearance="outline",
            options=[
                me.SelectOption(label=res, value=res)
                for res in selected_config.resolutions
            ],
            value=state.resolution,
            style=me.Style(),
        )

        # Video length (disabled)
        me.select(
            label="Video length",
            appearance="outline",
            options=[
                me.SelectOption(label=f"{state.video_length}s", value=str(state.video_length))
            ],
            value=str(state.video_length),
            disabled=True,
            style=me.Style(width="150px"),
        )
