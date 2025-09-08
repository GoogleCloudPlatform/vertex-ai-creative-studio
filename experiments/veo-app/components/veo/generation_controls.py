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

from state.veo_state import PageState
from config.veo_models import VEO_MODELS, get_veo_model_config


@me.component
def generation_controls():
    """Video generation controls, driven by the selected model's configuration."""
    state = me.state(PageState)
    selected_config = get_veo_model_config(state.veo_model)

    if not selected_config:
        me.text("Error: No model configuration found.")
        return

    # Correct state if it's inconsistent with the new model's configuration.
    if state.aspect_ratio not in selected_config.supported_aspect_ratios:
        state.aspect_ratio = selected_config.supported_aspect_ratios[0]
    
    # Handle duration correction
    if selected_config.supported_durations:
        if state.video_length not in selected_config.supported_durations:
            state.video_length = selected_config.default_duration
    elif not (selected_config.min_duration <= state.video_length <= selected_config.max_duration):
        state.video_length = selected_config.default_duration

    if state.resolution not in selected_config.resolutions:
        state.resolution = selected_config.resolutions[0]
    if state.veo_mode not in selected_config.supported_modes:
        state.veo_mode = selected_config.supported_modes[0]

    with me.box(style=me.Style(display="flex", flex_basis="row", gap=5)):
        # Aspect Ratio Selector
        me.select(
            label="aspect",
            appearance="outline",
            options=[
                me.SelectOption(label=f"{ratio} {'widescreen' if ratio == '16:9' else 'portrait'}", value=ratio)
                for ratio in selected_config.supported_aspect_ratios
            ],
            value=state.aspect_ratio,
            on_selection_change=on_selection_change_aspect,
            disabled=len(selected_config.supported_aspect_ratios) <= 1,
        )

        # Video Length Selector
        me.select(
            label="length",
            options=[
                me.SelectOption(label=f"{i} seconds", value=str(i))
                for i in (selected_config.supported_durations or range(selected_config.min_duration, selected_config.max_duration + 1))
            ],
            appearance="outline",
            style=me.Style(),
            value=str(state.video_length),
            on_selection_change=on_selection_change_length,
            disabled=(
                len(selected_config.supported_durations) <= 1
                if selected_config.supported_durations
                else selected_config.min_duration == selected_config.max_duration
            ),
        )

        # Resolution Selector
        me.select(
            label="resolution",
            options=[
                me.SelectOption(label=res, value=res)
                for res in selected_config.resolutions
            ],
            appearance="outline",
            style=me.Style(),
            value=state.resolution,
            on_selection_change=on_selection_change_resolution,
            disabled=len(selected_config.resolutions) <= 1,
        )

        # Prompt Enhancement Checkbox
        me.checkbox(
            label="auto-enhance prompt",
            checked=state.auto_enhance_prompt,
            on_change=on_change_auto_enhance_prompt,
            disabled=not selected_config.supports_prompt_enhancement,
        )

        # Model Selector
        me.select(
            label="model",
            options=[
                me.SelectOption(label=model.display_name, value=model.version_id)
                for model in VEO_MODELS
            ],
            appearance="outline",
            style=me.Style(),
            value=state.veo_model,
            on_selection_change=on_selection_change_model,
        )

        # Person Generation Selector
        me.select(
            label="person generation",
            appearance="outline",
            options=[
                me.SelectOption(label="Allow (All ages)", value="Allow (All ages)"),
                me.SelectOption(
                    label="Allow (Adults only)", value="Allow (Adults only)"
                ),
                me.SelectOption(label="Don't Allow", value="Don't Allow"),
            ],
            value=state.person_generation,
            on_selection_change=on_selection_change_person_generation,
        )


def on_selection_change_person_generation(e: me.SelectSelectionChangeEvent):
    """Handles changes to the person generation setting."""
    state = me.state(PageState)
    state.person_generation = e.value
    yield


def on_selection_change_length(e: me.SelectSelectionChangeEvent):
    """Adjust the video duration length in seconds based on user event"""
    state = me.state(PageState)
    state.video_length = int(e.value)


def on_selection_change_aspect(e: me.SelectSelectionChangeEvent):
    """Adjust aspect ratio based on user event."""
    state = me.state(PageState)
    state.aspect_ratio = e.value


def on_selection_change_resolution(e: me.SelectSelectionChangeEvent):
    """Adjust resolution based on user event."""
    state = me.state(PageState)
    state.resolution = e.value


def on_selection_change_model(e: me.SelectSelectionChangeEvent):
    """Adjust model based on user event and apply its constraints."""
    state = me.state(PageState)
    state.veo_model = e.value
    
    yield


def on_change_auto_enhance_prompt(e: me.CheckboxChangeEvent):
    """Toggle auto-enhance prompt"""
    state = me.state(PageState)
    state.auto_enhance_prompt = e.checked
