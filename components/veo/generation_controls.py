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

from common.analytics import log_ui_click
from config.veo_models import get_veo_model_config, VEO_MODELS
from state.state import AppState
from state.veo_state import PageState


@me.component
def generation_controls(
    on_selection_change_veo_model,
    on_selection_change_aspect_ratio,
    on_selection_change_resolution,
    on_change_video_length_select,
    on_selection_change_video_count,
    on_selection_change_person_generation,
    on_change_auto_enhance_prompt,
    on_change_generate_audio,
):
    """Generation controls for VEO."""
    state = me.state(PageState)
    selected_config = get_veo_model_config(state.veo_model)

    if not selected_config:
        return

    # Only show audio toggle for Veo 3 models
    show_audio_toggle = "3." in state.veo_model

    # Check for mode-specific overrides
    min_duration = selected_config.min_duration
    max_duration = selected_config.max_duration
    supported_durations = selected_config.supported_durations
    supported_aspect_ratios = selected_config.supported_aspect_ratios

    if (
        selected_config.mode_overrides
        and state.veo_mode in selected_config.mode_overrides
    ):
        override = selected_config.mode_overrides[state.veo_mode]
        if override.supported_durations:
            supported_durations = override.supported_durations
            min_duration = min(supported_durations)
            max_duration = max(supported_durations)
        if override.supported_aspect_ratios:
            supported_aspect_ratios = override.supported_aspect_ratios

    with me.box(style=me.Style(display="flex", flex_direction="row", gap=10)):
        # Model selection
        me.select(
            label="Model",
            appearance="outline",
            options=[
                me.SelectOption(label=model.display_name, value=model.version_id)
                for model in VEO_MODELS
            ],
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
            on_selection_change=on_selection_change_video_count,
            style=me.Style(width="100px"),
        )

        # Aspect ratio
        me.select(
            label="Aspect Ratio",
            appearance="outline",
            options=[
                me.SelectOption(label=ratio, value=ratio)
                for ratio in supported_aspect_ratios
            ],
            value=state.aspect_ratio,
            on_selection_change=on_selection_change_aspect_ratio,
            style=me.Style(width="150px"),
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
            on_selection_change=on_selection_change_resolution,
            style=me.Style(width="150px"),
        )

        # Video length
        me.select(
            label="Video length",
            appearance="outline",
            options=[
                me.SelectOption(label=f"{d}s", value=str(d))
                for d in (
                    supported_durations
                    if supported_durations
                    else range(min_duration, max_duration + 1)
                )
            ],
            value=str(state.video_length),
            on_selection_change=on_change_video_length_select,
            style=me.Style(width="150px"),
        )

        # Auto-enhance prompt
        if selected_config.supports_prompt_enhancement:
            # If the model mandates it, force it to checked and disable the checkbox
            is_required = selected_config.requires_prompt_enhancement
            me.checkbox(
                label="Auto-enhance prompt",
                on_change=on_change_auto_enhance_prompt,
                checked=True if is_required else state.auto_enhance_prompt,
                disabled=is_required,
            )

        # Generate audio
        if show_audio_toggle:
            me.checkbox(
                label="Generate audio",
                on_change=on_change_generate_audio,
                checked=state.generate_audio,
            )

        # Person generation
        me.select(
            label="Person Generation",
            appearance="outline",
            options=[
                me.SelectOption(label="Allow (All ages)", value="Allow (All ages)"),
                me.SelectOption(label="Allow (Adults only)", value="Allow (Adults only)"),
                me.SelectOption(label="Don't Allow", value="Don't Allow"),
            ],
            value=state.person_generation,
            on_selection_change=on_selection_change_person_generation,
        )