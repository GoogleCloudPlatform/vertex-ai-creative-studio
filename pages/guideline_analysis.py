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
"""Guideline Analysis page."""

import json
from dataclasses import asdict, dataclass, field
from typing import Callable

import mesop as me
from google.cloud import firestore

from common.metadata import (
    MediaItem,
    _create_media_item_from_dict,
    add_media_item_to_firestore,
    config,
    db,
    get_media_item_by_id,
)
from common.storage import store_to_gcs
from common.utils import create_display_url
from components.dialog import dialog
from components.header import header
from components.library.library_dialog import library_dialog
from components.media_tile.media_tile import media_tile
from components.page_scaffold import page_frame, page_scaffold
from components.scroll_sentinel.scroll_sentinel import scroll_sentinel
from models.gemini import describe_image, describe_video, evaluate_media_with_questions
from models.guideline_analysis import generate_guideline_criteria
from state.state import AppState


@me.stateclass
class PageState:
    """Guideline Analysis Page State"""

    selected_media_item_id: str | None = None
    additional_guidance: str = ""
    criteria: dict[str, list[str]] = field(default_factory=dict) # pylint: disable=E3701:invalid-field-call
    is_generating_criteria: bool = False
    criteria_error: str | None = None
    evaluations: dict[str, str] = field(default_factory=dict)  # Store as JSON strings # pylint: disable=E3701:invalid-field-call
    is_evaluating: bool = False
    evaluation_error: str | None = None
    show_chooser_dialog: bool = False
    chooser_is_loading: bool = False
    chooser_media_items: list[MediaItem] = field(default_factory=list) # pylint: disable=E3701:invalid-field-call
    chooser_last_doc_id: str = ""
    chooser_all_items_loaded: bool = False


@me.page(
    path="/guideline-analysis",
    title="Guideline Analysis",
)
def page():
    """Main Page."""
    with page_scaffold(page_name="guideline-analysis"): # pylint: disable=E1129:not-context-manager
        with page_frame(): # pylint: disable=E1129:not-context-manager
            header("Guideline Analysis", "rule")
            page_content()


def on_clear_click(e: me.ClickEvent):
    state = me.state(PageState)
    state.selected_media_item_id = None
    state.criteria = {}
    state.criteria_error = None
    state.evaluations = {}
    state.evaluation_error = None
    state.additional_guidance = ""
    yield


def on_additional_guidance_blur(e: me.InputEvent):
    state = me.state(PageState)
    state.additional_guidance = e.value


def on_describe_item_click(e: me.ClickEvent):
    state = me.state(PageState)
    if not state.selected_media_item_id:
        return

    item = get_media_item_by_id(state.selected_media_item_id)
    if not item:
        return

    gcs_uri = item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)
    if not gcs_uri:
        return

    original_prompt = item.prompt
    item.prompt = "Generating description..."
    add_media_item_to_firestore(item)
    yield

    try:
        description = ""
        mime_type = item.mime_type or ""
        if mime_type.startswith("video/"):
            description = describe_video(gcs_uri)
        else:
            description = describe_image(gcs_uri)
        item.prompt = description
    except Exception as ex:
        item.prompt = original_prompt
        print(f"Error describing media: {ex}")
    finally:
        add_media_item_to_firestore(item)
        yield


def on_evaluate_criteria_click(e: me.ClickEvent):
    state = me.state(PageState)
    if not state.selected_media_item_id or not state.criteria:
        return

    state.is_evaluating = True
    state.evaluations = {}
    state.evaluation_error = None
    yield

    item = get_media_item_by_id(state.selected_media_item_id)
    if not item:
        state.is_evaluating = False
        state.evaluation_error = "Could not find the selected media item."
        yield
        return

    gcs_uri = item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)
    if not gcs_uri:
        state.is_evaluating = False
        state.evaluation_error = "Media item does not have a valid image URI."
        yield
        return

    new_evaluations = {}
    try:
        for category, questions in state.criteria.items():
            if not questions:
                continue
            evaluation_result = evaluate_media_with_questions(
                media_uri=gcs_uri, mime_type=item.mime_type, questions=questions
            )
            yes_answers = sum(
                1 for answer in evaluation_result.answers if answer.answer
            )
            score_str = f"{yes_answers}/{len(questions)}"
            evaluation_dict = {
                "score": score_str,
                "details": [ans.model_dump() for ans in evaluation_result.answers],
            }
            new_evaluations[category] = json.dumps(evaluation_dict)
        state.evaluations = new_evaluations
    except Exception as ex:
        error_message = f"An error occurred during evaluation: {ex}"
        print(f"ERROR: {error_message}")
        state.evaluation_error = error_message
    finally:
        state.is_evaluating = False
        yield


def page_content():
    """The main content of the page."""
    state = me.state(PageState)
    render_chooser_dialog()

    item = None
    if state.selected_media_item_id:
        item = get_media_item_by_id(state.selected_media_item_id)

    with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
        with me.box(
            style=me.Style(
                width=400,
                background=me.theme_var("surface-container-lowest"),
                padding=me.Padding.all(16),
                border_radius=12,
            )
        ):
            me.text("Select a media asset to analyze")
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="row", align_items="center", gap=16
                )
            ):
                _uploader_placeholder(on_library_select=open_chooser_dialog)
                with me.content_button(on_click=on_clear_click, type="icon"):
                    me.icon("delete_sweep")

        with me.box(style=me.Style(flex_grow=1)):
            if item:
                with me.box(style=me.Style(display="flex", flex_direction="row", gap=16)):
                    with me.box(style=me.Style(width="50%")):
                        display_url = create_display_url(
                            item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)
                        )
                        if display_url:
                            mime_type = item.mime_type or ""
                            if mime_type.startswith("video/"):
                                me.video(src=display_url, style=me.Style(width="100%"))
                            else:
                                me.image(src=display_url, style=me.Style(width="100%"))
                        else:
                            me.text("No media preview")

                    with me.box(style=me.Style(width="50%")):
                        me.text("Prompt:", type="headline-6")
                        if item.prompt:
                            me.text(item.prompt)
                        else:
                            me.text("No prompt available. You can generate one below.")
                        me.button(
                            "Describe this item",
                            on_click=on_describe_item_click,
                            type="stroked",
                            style=me.Style(margin=me.Margin(top=8)),
                        )
                        me.textarea(
                            label="Additional Brand Guidelines",
                            on_blur=on_additional_guidance_blur,
                            value=state.additional_guidance,
                            style=me.Style(width="100%", margin=me.Margin(top=16)),
                        )

                with me.box(style=me.Style(margin=me.Margin(top=16))):
                    me.button(
                        "Generate Guideline Criteria",
                        on_click=on_generate_criteria_click,
                        disabled=not item.prompt,
                    )
                    if state.is_generating_criteria:
                        me.progress_spinner()

                    if state.criteria_error:
                        me.text(
                            state.criteria_error,
                            style=me.Style(color=me.theme_var("error")),
                        )

                    if state.criteria:
                        with me.box(style=me.Style(margin=me.Margin(top=16))):
                            for category, questions in state.criteria.items():
                                if questions:
                                    me.text(category, type="headline-6")
                                    for q in questions:
                                        me.text(f"- {q}")
                                    with me.box(
                                        style=me.Style(
                                            margin=me.Margin(top=8, bottom=8)
                                        )
                                    ):
                                        me.divider()

                            if not state.is_evaluating:
                                me.button(
                                    "Evaluate Criteria",
                                    on_click=on_evaluate_criteria_click,
                                    type="stroked",
                                    style=me.Style(margin=me.Margin(top=8)),
                                )

                    if state.is_evaluating:
                        me.progress_spinner()

                    if state.evaluation_error:
                        me.text(
                            state.evaluation_error,
                            style=me.Style(color=me.theme_var("error")),
                        )

                    if state.evaluations:
                        for category, evaluation_json in state.evaluations.items():
                            evaluation = json.loads(evaluation_json)
                            with me.box(style=me.Style(margin=me.Margin(top=16))):
                                with me.expansion_panel(
                                    title=f"{category} Score: {evaluation['score']}",
                                    icon="rule",
                                ):
                                    for detail in evaluation["details"]:
                                        with me.box(
                                            style=me.Style(
                                                display="flex",
                                                flex_direction="row",
                                                align_items="center",
                                                gap=8,
                                                margin=me.Margin(bottom=8),
                                            )
                                        ):
                                            if detail["answer"]:
                                                me.icon(
                                                    "check_circle",
                                                    style=me.Style(
                                                        color=me.theme_var("success")
                                                    ),
                                                )
                                            else:
                                                me.icon(
                                                    "cancel",
                                                    style=me.Style(
                                                        color=me.theme_var("error")
                                                    ),
                                                )
                                            me.text(detail["question"])
            else:
                me.text("No media item selected.")


def on_upload(e: me.UploadEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    file = e.files[0]
    gcs_url = store_to_gcs(
        "guideline_analysis_uploads",
        file.name,
        file.mime_type,
        file.getvalue(),
    )
    new_item = MediaItem(
        gcsuri=gcs_url,
        prompt="",
        mime_type=file.mime_type,
        user_email=app_state.user_email,
    )
    add_media_item_to_firestore(new_item)
    if new_item.id:
        state.selected_media_item_id = new_item.id
    else:
        print("ERROR: Could not get ID for newly uploaded item.")
    yield


@me.component
def _uploader_placeholder(on_library_select: Callable):
    with me.box(
        style=me.Style(
            height=100,
            width=100,
            border=me.Border.all(
                me.BorderSide(width=1, style="dashed", color=me.theme_var("outline"))
            ),
            border_radius=8,
            display="flex",
            flex_direction="column",
            align_items="center",
            justify_content="center",
            gap=8,
        )
    ):
        me.uploader(
            label="Upload Media",
            on_upload=on_upload,
            accepted_file_types=[
                "image/jpeg",
                "image/png",
                "image/webp",
                "video/mp4",
                "application/pdf",
            ],
            multiple=False,
        )
        with me.content_button(
            on_click=on_library_select,
            type="icon",
        ):
            me.icon("photo_library")


def get_all_media_for_chooser(
    page_size: int, start_after=None, *, user_email: str | None = None
) -> tuple[list[MediaItem], firestore.DocumentSnapshot | None]:
    if not db:
        return [], None
    # Fail closed: without a server-derived caller identity we must never list
    # another user's media. Return nothing rather than everything.
    if not user_email:
        return [], None
    try:
        query = (
            db.collection(config.GENMEDIA_COLLECTION_NAME)
            .where("user_email", "==", user_email)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
        )
        if start_after:
            query = query.start_after(start_after)
        query = query.limit(page_size)
        docs = list(query.stream())

        media_items = [
            _create_media_item_from_dict(doc.id, doc.to_dict())
            for doc in docs
            if doc.to_dict() is not None
        ]
        last_doc = docs[-1] if docs else None
        return media_items, last_doc
    except Exception as e:
        print(f"Error fetching all media for chooser: {e}")
        return [], None


@me.component
def render_chooser_dialog():
    state = me.state(PageState)

    def handle_item_selected(e: me.WebEvent):
        state = me.state(PageState)
        media_item_id = e.key
        state.show_chooser_dialog = False
        state.chooser_media_items = []
        state.selected_media_item_id = media_item_id
        yield

    def handle_load_more(e: me.WebEvent):
        app_state = me.state(AppState)
        if state.chooser_is_loading or state.chooser_all_items_loaded:
            return

        state.chooser_is_loading = True
        yield

        last_doc_ref = (
            db.collection(config.GENMEDIA_COLLECTION_NAME)
            .document(state.chooser_last_doc_id)
            .get()
        )
        new_items, last_doc = get_all_media_for_chooser(
            page_size=20,
            start_after=last_doc_ref,
            user_email=app_state.user_email,
        )

        for item in new_items:
            gcs_uri = item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)
            item.signed_url = create_display_url(gcs_uri) if gcs_uri else ""

        state.chooser_media_items.extend(new_items)
        state.chooser_last_doc_id = last_doc.id if last_doc else ""
        state.chooser_is_loading = False
        yield

    dialog_style = me.Style(
        width="95vw", height="80vh", display="flex", flex_direction="column"
    )

    with dialog(is_open=state.show_chooser_dialog, dialog_style=dialog_style): # pylint: disable=E1129:not-context-manager
        if state.show_chooser_dialog:
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="column", gap=16, flex_grow=1
                )
            ):
                with me.box(
                    style=me.Style(
                        display="flex",
                        flex_direction="row",
                        justify_content="space-between",
                        align_items="center",
                        width="100%",
                    )
                ):
                    me.text("Select a Media Asset from Library", type="headline-6")
                    with me.content_button(
                        type="icon",
                        on_click=lambda e: setattr(state, "show_chooser_dialog", False),
                    ):
                        me.icon("close")

                with me.box(
                    style=me.Style(
                        flex_grow=1, overflow_y="auto", padding=me.Padding.all(10)
                    )
                ):
                    if state.chooser_is_loading and not state.chooser_media_items:
                        me.progress_spinner()
                    else:
                        with me.box(
                            style=me.Style(
                                display="grid",
                                grid_template_columns="repeat(auto-fill, minmax(250px, 1fr))",
                                gap="16px",
                            )
                        ):
                            for item in state.chooser_media_items:
                                https_url = (
                                    item.signed_url
                                    if hasattr(item, "signed_url")
                                    else ""
                                )

                                render_type = "image"
                                if item.mime_type:
                                    if item.mime_type.startswith("video/"):
                                        render_type = "video"
                                    elif item.mime_type.startswith("audio/"):
                                        render_type = "audio"
                                elif https_url:
                                    if ".mp4" in https_url or ".webm" in https_url:
                                        render_type = "video"
                                    elif ".wav" in https_url or ".mp3" in https_url:
                                        render_type = "audio"

                                media_tile(
                                    key=item.id,
                                    on_click=handle_item_selected,
                                    media_type=render_type,
                                    https_url=https_url,
                                    pills_json="[]",
                                )
                        scroll_sentinel(
                            on_visible=handle_load_more,
                            is_loading=state.chooser_is_loading,
                            all_items_loaded=state.chooser_all_items_loaded,
                        )


def open_chooser_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    app_state = me.state(AppState)
    state.show_chooser_dialog = True
    state.chooser_is_loading = True
    state.chooser_media_items = []
    state.chooser_all_items_loaded = False
    state.chooser_last_doc_id = ""
    yield

    items, last_doc = get_all_media_for_chooser(
        page_size=20, user_email=app_state.user_email
    )

    for item in items:
        gcs_uri = item.gcsuri or (item.gcs_uris[0] if item.gcs_uris else None)
        item.signed_url = create_display_url(gcs_uri) if gcs_uri else ""

    state.chooser_media_items = items
    state.chooser_last_doc_id = last_doc.id if last_doc else ""
    if not last_doc:
        state.chooser_all_items_loaded = True
    state.chooser_is_loading = False
    yield


def on_generate_criteria_click(e: me.ClickEvent):
    state = me.state(PageState)
    if not state.selected_media_item_id:
        return

    item = get_media_item_by_id(state.selected_media_item_id)
    if not item or not item.prompt:
        return

    state.is_generating_criteria = True
    state.criteria = {}
    state.evaluations = {}
    state.criteria_error = None
    yield

    try:
        criteria_result = generate_guideline_criteria(
            item.prompt, state.additional_guidance
        )
        if not any(criteria_result.values()):
            state.criteria_error = "Failed to generate any guideline criteria. The model may have returned an empty response."
        else:
            state.criteria = criteria_result
    except Exception as ex:
        error_message = f"An error occurred while generating criteria: {ex}"
        print(f"Error generating criteria: {error_message}")
        state.criteria_error = error_message
    finally:
        state.is_generating_criteria = False
        yield
