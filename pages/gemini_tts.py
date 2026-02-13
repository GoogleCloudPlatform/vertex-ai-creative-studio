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

"""Gemini TTS page."""

import datetime
import json
import time
import uuid
from dataclasses import field

import mesop as me

import common.storage as storage
from common.analytics import log_ui_click, track_click
from common.metadata import MediaItem, add_media_item_to_firestore
from common.utils import create_display_url
from components.dialog import dialog, dialog_actions
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from components.pill import pill
from components.snackbar import snackbar
from config.gemini_tts import (
    GEMINI_TTS_LANGUAGES,
    GEMINI_TTS_MODEL_NAMES,
    GEMINI_TTS_MODELS,
    GEMINI_TTS_VOICES,
)
from models.audio_analysis import analyze_audio_file
from models.gemini import evaluate_tts_audio
from models.gemini_tts import synthesize_speech
from state.state import AppState

# Load about content from JSON
with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    GEMINI_TTS_INFO = next(
        (s for s in about_content["sections"] if s.get("id") == "gemini-tts"), None
    )

# Load presets from JSON
with open("config/tts_presets.json", "r") as f:
    tts_presets = json.load(f)["presets"]


@me.stateclass
class AudioMetricsState:
    mean_pitch_hz: float = 0.0
    pitch_std_hz: float = 0.0
    pitch_range_hz: float = 0.0
    jitter_percent: float = 0.0
    shimmer_db: float = 0.0
    hnr_db: float = 0.0
    estimated_tempo_bpm: float = 0.0
    duration_sec: float = 0.0


@me.stateclass
class TTSEvaluationState:
    has_result: bool = False
    quality_score: int = 0
    justification: str = ""
    key_tags: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    audio_metrics: AudioMetricsState = field(default_factory=AudioMetricsState)  # pylint: disable=invalid-field-call


@me.stateclass
class GeminiTtsState:
    prompt: str = "you are having a casual conversation with a friend and you are amused. say the following:"
    text: str = "[laughing] oh my god! [sigh] did you see what he is wearing?"
    selected_model: str = GEMINI_TTS_MODEL_NAMES[0]
    selected_voice: str = "Callirrhoe"
    selected_language: str = "en-US"
    is_generating: bool = False
    audio_gcs_uri: str = ""
    audio_display_url: str = ""
    error: str = ""
    info_dialog_open: bool = False
    show_snackbar: bool = False
    snackbar_message: str = ""
    is_evaluating: bool = False
    evaluation_result: TTSEvaluationState = field(default_factory=TTSEvaluationState)  # pylint: disable=invalid-field-call


@me.page(
    path="/gemini-tts",
    title="Gemini TTS",
)
def page():
    """Renders the Gemini TTS page."""
    state = me.state(GeminiTtsState)

    with page_scaffold(page_name="gemini-tts"):  # pylint: disable=E1129:not-context-manager
        gemini_tts_page_content()


def gemini_tts_page_content():
    state = me.state(GeminiTtsState)
    with page_frame():  # pylint: disable=E1129:not-context-manager
        header(
            "Gemini Text-to-Speech",
            "record_voice_over",
            show_info_button=True,
            on_info_click=open_info_dialog,
        )

        if state.info_dialog_open:
            with dialog(is_open=state.info_dialog_open):  # pylint: disable=E1129
                me.text(GEMINI_TTS_INFO["title"], type="headline-6")
                me.markdown(GEMINI_TTS_INFO["description"])
                with dialog_actions():  # pylint: disable=E1129
                    me.button("Close", on_click=close_info_dialog, type="flat")

        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="row",
                gap=24,
            ),
        ):
            # Left column (controls)
            with me.box(
                style=me.Style(
                    width=500,
                    background=me.theme_var("surface-container-lowest"),
                    padding=me.Padding.all(16),
                    border_radius=12,
                    display="flex",
                    flex_direction="column",
                    gap=3,
                )
            ):
                me.textarea(
                    label="Text to Synthesize",
                    on_blur=on_blur_text,
                    value=state.text,
                    rows=5,
                    style=me.Style(width="100%"),
                    appearance="outline",
                    autosize=True,
                )
                me.textarea(
                    label="Style Prompt",
                    on_blur=on_blur_prompt,
                    value=state.prompt,
                    rows=3,
                    style=me.Style(width="100%"),
                    appearance="outline",
                    autosize=True,
                )
                with me.box(
                    style=me.Style(display="flex", flex_direction="row", gap=16),
                ):
                    me.select(
                        label="Model",
                        options=[
                            me.SelectOption(
                                label=GEMINI_TTS_MODELS[m]["label"], value=m,
                            )
                            for m in GEMINI_TTS_MODEL_NAMES
                        ],
                        on_selection_change=on_select_model,
                        value=state.selected_model,
                        style=me.Style(flex_grow=1, width=250),
                        appearance="outline",
                    )
                    me.text(GEMINI_TTS_MODELS[state.selected_model]["description"])
                with me.box(
                    style=me.Style(display="flex", flex_direction="row", gap=16),
                ):
                    me.select(
                        label="Voice",
                        options=[
                            me.SelectOption(label=v, value=v) for v in GEMINI_TTS_VOICES
                        ],
                        on_selection_change=on_select_voice,
                        value=state.selected_voice,
                        style=me.Style(flex_grow=1),
                        appearance="outline",
                    )
                    me.select(
                        label="Language",
                        options=[
                            me.SelectOption(label=lang, value=code)
                            for lang, code in GEMINI_TTS_LANGUAGES.items()
                        ],
                        on_selection_change=on_select_language,
                        value=state.selected_language,
                        style=me.Style(flex_grow=1, width=250),
                        appearance="outline",
                    )
                with me.box(
                    style=me.Style(display="flex", flex_direction="row", gap=16)
                ):
                    me.button(
                        "Generate",
                        on_click=on_click_generate,
                        type="raised",
                        disabled=state.is_generating,
                    )
                    me.button(
                        "Clear",
                        on_click=on_click_clear,
                        type="stroked",
                    )

                me.box(style=me.Style(height=16))

                me.text("Try it out")

                # Dynamically render presets based on selected language
                with me.box(
                    style=me.Style(
                        display="flex", flex_direction="row", gap=16, flex_wrap="wrap"
                    ),
                ):
                    filtered_presets = [
                        p
                        for p in tts_presets
                        if p["language_code"] == state.selected_language
                    ]
                    for i, preset in enumerate(filtered_presets):
                        me.button(
                            preset["name"],
                            key=str(i),  # Use index as key
                            on_click=on_click_preset,
                            # type="stroked",
                        )

            # Output display
            with me.box(
                style=me.Style(
                    flex_grow=1,
                    display="flex",
                    flex_direction="column",
                    align_items="center",
                    justify_content="center",
                    border=me.Border.all(me.BorderSide(width=1, style="solid")),
                    border_radius=12,
                    padding=me.Padding.all(16),
                )
            ):
                if state.is_generating:
                    me.progress_spinner()
                    me.text("Generating audio...")
                elif state.audio_display_url:
                    me.audio(src=state.audio_display_url)

                    # Evaluation Section
                    if state.is_evaluating:
                        with me.box(
                            style=me.Style(
                                margin=me.Margin(top=24),
                                display="flex",
                                flex_direction="column",
                                align_items="center",
                                gap=8,
                            )
                        ):
                            me.progress_spinner(diameter=24)
                            me.text("Listening closely to the audio...")
                    elif state.evaluation_result.has_result:
                        with me.box(
                            style=me.Style(
                                margin=me.Margin(top=24),
                                padding=me.Padding.all(16),
                                background=me.theme_var("surface-container-low"),
                                border_radius=8,
                                width="100%",
                            )
                        ):
                            me.text("AI Quality Assurance", type="headline-6")
                            me.text(
                                f"Quality Score: {state.evaluation_result.quality_score}/100",
                                type="subtitle-1",
                                style=me.Style(
                                    font_weight="bold", color=me.theme_var("primary")
                                ),
                            )
                            me.markdown(state.evaluation_result.justification)
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    flex_wrap="wrap",
                                    gap=8,
                                    margin=me.Margin(top=8),
                                )
                            ):
                                for tag in state.evaluation_result.key_tags:
                                    pill(label=tag, pill_type="genre")

                            # Technical Metrics Expansion Panel
                            me.box(style=me.Style(height=8))
                            with me.expansion_panel(
                                title="Technical Audio Metrics", icon="graphic_eq"
                            ):
                                metrics = state.evaluation_result.audio_metrics
                                with me.box(
                                    style=me.Style(
                                        display="grid",
                                        grid_template_columns="1fr 1fr",
                                        gap=0,
                                    )
                                ):
                                    me.text(
                                        f"Duration: {metrics.duration_sec:.2f}s",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"Tempo: {metrics.estimated_tempo_bpm:.1f} BPM",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"Mean Pitch: {metrics.mean_pitch_hz:.1f} Hz",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"Pitch Range: {metrics.pitch_range_hz:.1f} Hz",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"Pitch Std Dev: {metrics.pitch_std_hz:.1f} Hz",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"Jitter: {metrics.jitter_percent:.2f}%",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"Shimmer: {metrics.shimmer_db:.2f} dB",
                                        style=me.Style(font_weight="bold"),
                                    )
                                    me.text(
                                        f"HNR: {metrics.hnr_db:.1f} dB",
                                        style=me.Style(font_weight="bold"),
                                    )

                else:
                    me.text("Generated audio will appear here.")
        snackbar(is_visible=state.show_snackbar, label=state.snackbar_message)


def on_blur_text(e: me.InputBlurEvent):
    """Handles text input."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="gemini_tts_text_input",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(GeminiTtsState)
    state.text = e.value


def on_blur_prompt(e: me.InputBlurEvent):
    """Handles prompt input."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="gemini_tts_prompt_input",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(GeminiTtsState)
    state.prompt = e.value


def on_select_model(e: me.SelectSelectionChangeEvent):
    """Handles model selection."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="gemini_tts_model_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(GeminiTtsState)
    state.selected_model = e.value


def on_select_voice(e: me.SelectSelectionChangeEvent):
    """Handles voice selection."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="gemini_tts_voice_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(GeminiTtsState)
    state.selected_voice = e.value


def on_select_language(e: me.SelectSelectionChangeEvent):
    """Handles language selection."""
    app_state = me.state(AppState)
    log_ui_click(
        element_id="gemini_tts_language_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(GeminiTtsState)
    state.selected_language = e.value
    yield


@track_click(element_id="gemini_tts_preset_button")
def on_click_preset(e: me.ClickEvent):
    """Handles preset button click."""
    state = me.state(GeminiTtsState)
    preset_index = int(e.key)
    # Filter presets again to get the correct one based on the current language
    filtered_presets = [
        p for p in tts_presets if p["language_code"] == state.selected_language
    ]
    preset = filtered_presets[preset_index]

    state.prompt = preset["prompt"]
    state.text = preset["text"]
    state.selected_voice = preset["voice"]
    yield


@track_click(element_id="gemini_tts_clear_button")
def on_click_clear(e: me.ClickEvent):
    """Resets the page state to its default values."""
    state = me.state(GeminiTtsState)
    state.prompt = "you are having a casual conversation with a friend and you are amused. say the following:"
    state.text = "[laughing] oh my god! [sigh] did you see what he is wearing?"
    state.selected_model = GEMINI_TTS_MODEL_NAMES[0]
    state.selected_voice = "Callirrhoe"
    state.selected_language = "en-US"
    state.audio_gcs_uri = ""
    state.audio_display_url = ""
    state.error = ""
    state.is_generating = False
    state.is_evaluating = False
    state.evaluation_result.has_result = False
    state.evaluation_result.quality_score = 0
    state.evaluation_result.justification = ""
    state.evaluation_result.key_tags = []
    # Reset metrics
    state.evaluation_result.audio_metrics.mean_pitch_hz = 0.0
    state.evaluation_result.audio_metrics.pitch_std_hz = 0.0
    state.evaluation_result.audio_metrics.pitch_range_hz = 0.0
    state.evaluation_result.audio_metrics.jitter_percent = 0.0
    state.evaluation_result.audio_metrics.shimmer_db = 0.0
    state.evaluation_result.audio_metrics.hnr_db = 0.0
    state.evaluation_result.audio_metrics.estimated_tempo_bpm = 0.0
    state.evaluation_result.audio_metrics.duration_sec = 0.0
    yield


@track_click(element_id="gemini_tts_generate_button")
def on_click_generate(e: me.ClickEvent):
    """Handles generate button click."""
    state = me.state(GeminiTtsState)
    app_state = me.state(AppState)
    state.is_generating = True
    state.audio_display_url = ""
    state.error = ""
    state.evaluation_result.has_result = False
    gcs_url = ""
    yield

    try:
        audio_bytes = synthesize_speech(
            text=state.text,
            prompt=state.prompt,
            model_name=state.selected_model,
            voice_name=state.selected_voice,
            language_code=state.selected_language,
        )

        file_name = f"gemini-tts-{uuid.uuid4()}.wav"

        gcs_url = storage.store_to_gcs(
            folder="gemini-tts-audio",
            file_name=file_name,
            mime_type="audio/wav",
            contents=audio_bytes,
        )

        state.audio_gcs_uri = gcs_url
        state.audio_display_url = create_display_url(gcs_url)

    except Exception as ex:
        print(f"ERROR: Failed to generate audio. Details: {ex}")
        yield from _show_snackbar(state, f"An error occurred: {ex}")

    finally:
        state.is_generating = False
        yield

    # Add to library and start evaluation if generation was successful
    if gcs_url:
        # 1. Add to library
        try:
            item = MediaItem(
                user_email=app_state.user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=state.text,  # The main text is the core prompt
                comment=f"Voice: {state.selected_voice}, Style Prompt: {state.prompt}",
                model=state.selected_model,
                mime_type="audio/wav",
                gcsuri=gcs_url,
                voice=state.selected_voice,
                language_code=state.selected_language,
                style_prompt=state.prompt,
            )
            add_media_item_to_firestore(item)
        except Exception as ex:
            print(f"CRITICAL: Failed to store metadata: {ex}")

        # 2. Start Evaluation (Gemini + Technical Metrics)
        state.is_evaluating = True
        yield
        try:
            # Run both evaluations. In a real async setup these could be parallel,
            # but sequential is fine for now as they are reasonably fast.

            # Gemini Evaluation
            eval_result = evaluate_tts_audio(
                audio_uri=state.audio_gcs_uri,
                original_text=state.text,
                generation_prompt=state.prompt,
            )
            state.evaluation_result.quality_score = eval_result.quality_score
            state.evaluation_result.justification = eval_result.justification
            state.evaluation_result.key_tags = eval_result.key_tags

            # Technical Audio Analysis
            audio_metrics = analyze_audio_file(state.audio_gcs_uri)
            state.evaluation_result.audio_metrics.mean_pitch_hz = (
                audio_metrics.mean_pitch_hz
            )
            state.evaluation_result.audio_metrics.pitch_std_hz = (
                audio_metrics.pitch_std_hz
            )
            state.evaluation_result.audio_metrics.pitch_range_hz = (
                audio_metrics.pitch_range_hz
            )
            state.evaluation_result.audio_metrics.jitter_percent = (
                audio_metrics.jitter_percent
            )
            state.evaluation_result.audio_metrics.shimmer_db = audio_metrics.shimmer_db
            state.evaluation_result.audio_metrics.hnr_db = audio_metrics.hnr_db
            state.evaluation_result.audio_metrics.estimated_tempo_bpm = (
                audio_metrics.estimated_tempo_bpm
            )
            state.evaluation_result.audio_metrics.duration_sec = (
                audio_metrics.duration_sec
            )

            state.evaluation_result.has_result = True

        except Exception as ex:
            print(f"ERROR: Failed to evaluate audio. Details: {ex}")
            yield from _show_snackbar(state, f"Evaluation failed: {ex}")
        finally:
            state.is_evaluating = False
            yield


def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    state = me.state(GeminiTtsState)
    state.info_dialog_open = True
    yield


def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(GeminiTtsState)
    state.info_dialog_open = False
    yield


def _show_snackbar(state: GeminiTtsState, message: str):
    state.snackbar_message = message
    state.show_snackbar = True
    yield
    time.sleep(3)
    state.show_snackbar = False
    yield
