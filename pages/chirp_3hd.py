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

"""Chirp3 HD TTS page."""

import datetime
import uuid
import json
from dataclasses import field

import mesop as me
from common.analytics import log_ui_click, track_click

import common.storage as storage
from common.utils import create_display_url
from common.metadata import MediaItem, add_media_item_to_firestore
from components.dialog import dialog, dialog_actions
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from config.chirp_3hd import (
    CHIRP3_HD_VOICES,
    CHIRP3_HD_LANGUAGES,
    CHIRP3_HD_ENCODINGS,
)
from models.chirp_3hd import synthesize_chirp_speech
from state.state import AppState

# Load about content from JSON
with open("config/about_content.json", "r") as f:
    about_content = json.load(f)
    CHIRP3_HD_INFO = next(
        (s for s in about_content["sections"] if s.get("id") == "chirp-3hd"), None
    )


@me.stateclass
class Chirp3hdState:
    text: str = "Hello, Chirp is the latest generation of Google's Text-to-Speech technology."
    selected_voice: str = "Orus"
    selected_language: str = "en-US"
    speaking_rate: float = 1.0
    # pitch: float = 0.0 # Disabled pending API support
    volume_gain_db: float = 0.0
    is_generating: bool = False
    audio_gcs_uri: str = ""
    audio_display_url: str = ""
    info_dialog_open: bool = False
    # For error dialog
    show_error_dialog: bool = False
    error_message: str = ""
    # For custom pronunciations
    custom_pronunciations: list[dict[str, str]] = field(default_factory=list) # pylint: disable=invalid-field-call
    current_phrase_input: str = ""
    current_pronunciation_input: str = ""
    selected_encoding: str = "PHONETIC_ENCODING_X_SAMPA"


@me.page(
    path="/chirp-3hd",
    title="Chirp3 HD TTS",
)
def page():
    """Renders the Chirp3 HD TTS page."""
    state = me.state(Chirp3hdState)

    with page_scaffold(page_name="chirp_3hd"):  # pylint: disable=E1129
        with page_frame():  # pylint: disable=E1129
            header(
                "Chirp3 HD Text-to-Speech",
                "graphic_eq",
                show_info_button=True,
                on_info_click=open_info_dialog,
            )

            # Info Dialog
            if state.info_dialog_open:
                with dialog(is_open=state.info_dialog_open):  # pylint: disable=E1129
                    me.text(CHIRP3_HD_INFO["title"], type="headline-6")
                    me.markdown(CHIRP3_HD_INFO["description"])
                    with dialog_actions():  # pylint: disable=E1129
                        me.button("Close", on_click=close_info_dialog, type="flat")
            
            # Error Dialog
            if state.show_error_dialog:
                with dialog(is_open=state.show_error_dialog):  # pylint: disable=E1129
                    me.text("Generation Error", type="headline-6", style=me.Style(color=me.theme_var("error")))
                    me.text(state.error_message, style=me.Style(margin=me.Margin(top=16)))
                    with dialog_actions():  # pylint: disable=E1129
                        me.button("Close", on_click=close_error_dialog, type="flat")

            with me.box(
                style=me.Style(
                    padding=me.Padding.all(24),
                    display="flex",
                    flex_direction="row",
                    gap=24,
                )
            ):
                # Left column (controls)
                with me.box(
                    style=me.Style(
                        width=800,
                        background=me.theme_var("surface-container-lowest"),
                        #padding=me.Padding.all(16),
                        border_radius=12,
                        display="flex",
                        flex_direction="column",
                        gap=16,
                    ),
                ):
                    me.textarea(
                        label="Text to Synthesize",
                        on_blur=on_blur_text,
                        value=state.text,
                        rows=5,
                        style=me.Style(width="100%"),
                        appearance="outline",
                    )
                    with me.box(
                        style=me.Style(
                            display="flex", flex_direction="row", gap=16,
                        )
                    ):
                        me.select(
                            label="Voice",
                            options=[
                                me.SelectOption(label=v, value=v)
                                for v in CHIRP3_HD_VOICES
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
                                for lang, code in CHIRP3_HD_LANGUAGES.items()
                            ],
                            on_selection_change=on_select_language,
                            value=state.selected_language,
                            style=me.Style(flex_grow=1, width=300),
                            appearance="outline",
                        )
                    with me.expansion_panel(
                        key="advanced_controls",
                        icon="tune",
                        title="",
                        description="Advanced Controls",
                    ):
                        # Pace, Volume Controls Section
                        with me.box(style=me.Style(display="flex", flex_direction="row", justify_content="space-around", gap=8)):
                            with me.box():
                                me.text(f"Pace: {state.speaking_rate:.2f}")
                                me.slider(on_value_change=on_change_pace, min=0.25, max=2.0, value=state.speaking_rate, step=0.05)
                            with me.box():
                                me.text(f"Volume Gain: {state.volume_gain_db:.1f} dB")
                                me.slider(on_value_change=on_change_volume, min=-96.0, max=16.0, value=state.volume_gain_db, step=0.5)
                        
                        # Custom Pronunciations Section
                        me.text("Custom Pronunciations", style=me.Style(font_weight=500, margin=me.Margin(top=8)))
                        with me.box(style=me.Style(display="flex", flex_direction="row", gap=16, align_items="baseline")):
                            me.input(label="Phrase", on_blur=on_blur_phrase, style=me.Style(flex_grow=1,font_size="smaller"), value=state.current_phrase_input,appearance="outline",)
                            me.input(label="Pronunciation", on_blur=on_blur_pronunciation, style=me.Style(flex_grow=1,font_size="smaller"), value=state.current_pronunciation_input, appearance="outline",)
                            me.select(
                                label="Encoding",
                                options=[
                                    me.SelectOption(label=lang, value=code)
                                    for lang, code in CHIRP3_HD_ENCODINGS.items()
                                ],
                                on_selection_change=on_select_encoding,
                                value=state.selected_encoding,
                                style=me.Style(flex_grow=1,font_size="smaller"),
                                appearance="outline",
                            )
                            with me.content_button(type="icon", on_click=on_add_pronunciation,):
                                me.icon("add")
                            #me.button("Add", on_click=on_add_pronunciation, type="stroked")
                    
                        if state.custom_pronunciations:
                            with me.box(style=me.Style(margin=me.Margin(top=16))):
                                for i, p in enumerate(state.custom_pronunciations):
                                    with me.box(style=me.Style(display="flex", flex_direction="row", align_items="center", gap=8, margin=me.Margin(bottom=8))):
                                        me.text(f'{p["phrase"]} → {p["pronunciation"]}', style=me.Style(flex_grow=1))
                                        with me.content_button(key=str(i), on_click=on_remove_pronunciation, type="icon"):
                                            me.icon("delete")

                    with me.box(
                        style=me.Style(display="flex", flex_direction="row", gap=16, margin=me.Margin(top=16))
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

                # Output display
                with me.box(
                    style=me.Style(
                        flex_grow=1,
                        display="flex",
                        flex_direction="column",
                        align_items="center",
                        justify_content="center",
                        border=me.Border.all(
                            me.BorderSide(width=1, style="solid")
                        ),
                        border_radius=12,
                        padding=me.Padding.all(16),
                    )
                ):
                    if state.is_generating:
                        me.progress_spinner()
                        me.text("Generating audio...")
                    elif state.audio_display_url:
                        me.audio(src=state.audio_display_url)
                    else:
                        me.text("Generated audio will appear here.")

def on_blur_text(e: me.InputBlurEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_text_input",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(Chirp3hdState)
    state.text = e.value

def on_blur_phrase(e: me.InputBlurEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_phrase_input",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(Chirp3hdState)
    state.current_phrase_input = e.value

def on_blur_pronunciation(e: me.InputBlurEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_pronunciation_input",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(Chirp3hdState)
    state.current_pronunciation_input = e.value

def on_select_voice(e: me.SelectSelectionChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_voice_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(Chirp3hdState)
    state.selected_voice = e.value

def on_select_language(e: me.SelectSelectionChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_language_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(Chirp3hdState)
    state.selected_language = e.value
    yield

def on_select_encoding(e: me.SelectSelectionChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_encoding_select",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    state = me.state(Chirp3hdState)
    state.selected_encoding = e.value

def on_change_pace(e: me.SliderValueChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_pace_slider",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    me.state(Chirp3hdState).speaking_rate = e.value

# def on_change_pitch(e: me.SliderValueChangeEvent):
#     me.state(Chirp3hdState).pitch = e.value

def on_change_volume(e: me.SliderValueChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="chirp_volume_slider",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    me.state(Chirp3hdState).volume_gain_db = e.value

@track_click(element_id="chirp_add_pronunciation_button")
def on_add_pronunciation(e: me.ClickEvent):
    state = me.state(Chirp3hdState)
    if state.current_phrase_input and state.current_pronunciation_input:
        state.custom_pronunciations.append({
            "phrase": state.current_phrase_input,
            "pronunciation": state.current_pronunciation_input,
        })
        state.current_phrase_input = ""
        state.current_pronunciation_input = ""
        yield

@track_click(element_id="chirp_remove_pronunciation_button")
def on_remove_pronunciation(e: me.ClickEvent):
    state = me.state(Chirp3hdState)
    index_to_remove = int(e.key)
    state.custom_pronunciations.pop(index_to_remove)
    yield

@track_click(element_id="chirp_generate_button")
def on_click_generate(e: me.ClickEvent):
    """Handles generate button click."""
    state = me.state(Chirp3hdState)
    state.is_generating = True
    state.audio_url = ""
    state.error_message = ""
    state.show_error_dialog = False
    gcs_url = ""
    yield

    print("--- DEBUG: Preparing to call synthesize_chirp_speech ---")
    print(f"Type of 'text': {type(state.text)}, Value: {state.text}")
    print(f"Type of 'voice_name': {type(state.selected_voice)}, Value: {state.selected_voice}")
    print(f"Type of 'language_code': {type(state.selected_language)}, Value: {state.selected_language}")
    print(f"Type of 'speaking_rate': {type(state.speaking_rate)}, Value: {state.speaking_rate}")
    print(f"Type of 'volume_gain_db': {type(state.volume_gain_db)}, Value: {state.volume_gain_db}")
    print(f"Type of 'pronunciations': {type(state.custom_pronunciations)}, Value: {state.custom_pronunciations}")
    print(f"Type of 'phonetic_encoding': {type(state.selected_encoding)}, Value: {state.selected_encoding}")
    print("----------------------------------------------------")

    try:
        audio_bytes = synthesize_chirp_speech(
            text=state.text,
            voice_name=state.selected_voice,
            language_code=state.selected_language,
            speaking_rate=state.speaking_rate,
            # pitch=state.pitch,
            volume_gain_db=state.volume_gain_db,
            pronunciations=state.custom_pronunciations,
            phonetic_encoding=state.selected_encoding,
        )

        file_name = f"chirp3-hd-{uuid.uuid4()}.wav"

        gcs_url = storage.store_to_gcs(
            folder="chirp3-hd-audio",
            file_name=file_name,
            mime_type="audio/wav",
            contents=audio_bytes,
        )

        state.audio_gcs_uri = gcs_url
        state.audio_display_url = create_display_url(gcs_url)

    except Exception as ex:
        print(f"ERROR: Failed to generate Chirp3 HD audio. Details: {ex}")
        state.error_message = str(ex)
        state.show_error_dialog = True

    finally:
        state.is_generating = False
        yield

    # Add to library
    if gcs_url:
        try:
            item = MediaItem(
                user_email=me.state(AppState).user_email,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                prompt=state.text,  # The main text is the core prompt
                comment=f"Voice: {state.selected_voice}, Pace: {state.speaking_rate:.2f}, Volume: {state.volume_gain_db:.1f}dB",
                model="Chirp3 HD",
                mime_type="audio/wav",
                gcsuri=gcs_url,
                custom_pronunciations=state.custom_pronunciations,
                voice=state.selected_voice,
                pace=state.speaking_rate,
                volume_gain_db=state.volume_gain_db,
                language_code=state.selected_language
            )
            add_media_item_to_firestore(item)
            me.state(AppState).snackbar_message = "Audio saved to library"
        except Exception as ex:
            print(f"CRITICAL: Failed to store metadata: {ex}")
            me.state(AppState).snackbar_message = "Error saving audio to library"


@track_click(element_id="chirp_clear_button")
def on_click_clear(e: me.ClickEvent):
    """Resets the page state to its default values."""
    state = me.state(Chirp3hdState)
    state.text = "Hello, Chirp is the latest generation of Google's Text-to-Speech technology."
    state.selected_voice = "Orus"
    state.selected_language = "en-US"
    state.speaking_rate = 1.0
    # state.pitch = 0.0
    state.volume_gain_db = 0.0
    state.custom_pronunciations = []
    state.current_phrase_input = ""
    state.current_pronunciation_input = ""
    state.selected_encoding = "PHONETIC_ENCODING_X_SAMPA"
    state.audio_gcs_uri = ""
    state.audio_display_url = ""
    state.error_message = ""
    state.show_error_dialog = False
    state.is_generating = False
    yield


def open_info_dialog(e: me.ClickEvent):
    """Open the info dialog."""
    state = me.state(Chirp3hdState)
    state.info_dialog_open = True
    yield


def close_info_dialog(e: me.ClickEvent):
    """Close the info dialog."""
    state = me.state(Chirp3hdState)
    state.info_dialog_open = False
    yield

def close_error_dialog(e: me.ClickEvent):
    """Close the error dialog."""
    state = me.state(Chirp3hdState)
    state.show_error_dialog = False
    state.error_message = ""
    yield
