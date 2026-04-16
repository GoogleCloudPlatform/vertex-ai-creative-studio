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
from typing import Any, Dict, Optional, Union

import mesop as me
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field, ValidationError

from components.header import header
from config.default import Default
from models.parsers import parse_evaluation_markdown
from models.prompts import VIDEO_PROMPT_HEALTH_CHECKLIST
from services.llm_client import LLMClient
from state.state import AppState


# Pydantic Models for structured response
class ChecklistItemDetail(BaseModel):
    """Represents the details of a single checklist item."""

    score: bool
    explanation: Optional[str] = None


class IssueDetail(BaseModel):
    """Represents the structured details of an identified issue."""

    issue_name: str
    location_in_prompt: str
    rationale: str


class CategoryData(BaseModel):
    """Represents the data for a single category in the checklist."""

    items: Dict[str, bool] = Field(default_factory=dict)
    details: Optional[Dict[str, Union[IssueDetail, str]]] = (
        None  # Can hold structured issue details or simple string explanations
    )
    explanation: Optional[str] = None  # For overall category explanation

    @classmethod
    def parse_category_data(cls, data: Dict[str, Any]) -> "CategoryData":
        """Parses a dictionary into a CategoryData object.

        Args:
            data: The dictionary to parse.

        Returns:
            A CategoryData object.
        """
        items = {}
        details_dict = {}  # Initialize as an empty dict
        category_explanation_str = None

        if isinstance(data, dict):
            # Correctly parse nested items
            raw_items = data.get("items")
            if isinstance(raw_items, dict):
                for key, value in raw_items.items():
                    if isinstance(value, bool):
                        items[key] = value

            raw_details = data.get("details")
            if isinstance(raw_details, dict):
                for key, value in raw_details.items():
                    if isinstance(value, dict):
                        try:
                            # Attempt to parse as a structured IssueDetail
                            details_dict[key] = IssueDetail(**value)
                        except ValidationError:
                            # If it fails, treat it as a plain string (or handle error appropriately)
                            details_dict[key] = str(value)
                    else:
                        # Keep it as a string if it's not a dictionary
                        details_dict[key] = str(value)

            category_explanation_str = data.get("explanation")
            if not isinstance(category_explanation_str, str):
                category_explanation_str = None

        return cls(
            items=items,
            details=details_dict if details_dict else None,
            explanation=category_explanation_str,
        )


class ParsedChecklistResponse(BaseModel):
    """Represents the entire checklist response."""

    categories: Dict[str, CategoryData] = Field(default_factory=dict)

    @classmethod
    def from_json_dict(cls, json_dict: Dict[str, Any]) -> "ParsedChecklistResponse":
        """Creates a ParsedChecklistResponse from a JSON dictionary.

        Args:
            json_dict: The JSON dictionary to parse.

        Returns:
            A ParsedChecklistResponse object.
        """
        parsed_categories = {}
        for cat_name, cat_data in json_dict.items():
            if isinstance(cat_data, dict):
                parsed_categories[cat_name] = CategoryData.parse_category_data(cat_data)
            else:
                # Handle cases where a category might not be a dict as expected
                print(
                    f"Warning: Category '{cat_name}' data is not a dictionary, skipping."
                )
                parsed_categories[cat_name] = CategoryData()  # empty category
        return cls(categories=parsed_categories)


@me.stateclass
class PageState:
    """Local page state for the checklist page."""

    processing: bool = False
    prompt_input: str = ""
    prompt_textarea_key: int = 0
    prompt_placeholder: str = ""
    prompt_response: str = ""  # Raw text from Gemini
    # Store the successfully parsed JSON as a string to avoid Mesop deserialization issues
    parsed_response_json_str: Optional[str] = None
    # commentary_prefix: Optional[str] = None # No longer storing prefix
    commentary_suffix: Optional[str] = None


def video_checklist_page_content(app_state: me.state):
    """Renders the main content of the checklist page.

    Args:
        app_state: The global application state.
    """
    state = me.state(PageState)

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
                header("Video Prompt Health Checklist", "movie")
                me.text(
                    "Receive a quick checkup of your video prompt using the video prompt health checklist"
                )
                me.box(style=me.Style(height=16))
                gemini_prompt_input()
                me.box(style=me.Style(height=16))

                if state.processing:
                    with me.box(
                        style=me.Style(
                            display="grid",
                            justify_content="center",
                            justify_items="center",
                        )
                    ):
                        me.progress_spinner()
                        me.text("Linting prompt...")

                elif state.parsed_response_json_str or state.commentary_suffix:
                    if state.parsed_response_json_str:
                        try:
                            raw_dict = json.loads(state.parsed_response_json_str)
                            pydantic_response = ParsedChecklistResponse.from_json_dict(
                                raw_dict
                            )
                            # me.text("Evaluation Results", style=me.Style(font_weight="bold", font_size=18, margin=me.Margin(bottom=12)))
                            render_pydantic_response(pydantic_response)
                        except (json.JSONDecodeError, ValidationError) as e:
                            me.text(
                                "Error displaying structured results:",
                                style=me.Style(color="red", font_weight="bold"),
                            )
                            me.text(f"Details: {str(e)}")
                            # If JSON parsing failed but we have a suffix, suffix will be shown below.
                            # If no suffix either, show the full raw response.
                            if not state.commentary_suffix:
                                me.text(
                                    "Raw response:",
                                    style=me.Style(
                                        font_weight="bold", margin=me.Margin(top=8)
                                    ),
                                )
                                me.markdown(text=f"```\n{state.prompt_response}\n```")

                    # Display suffix commentary if it exists, in an expansion panel
                    if state.commentary_suffix and state.commentary_suffix.strip():
                        me.box(style=me.Style(height=28))
                        with me.expansion_panel(
                            title="View Additional Commentary", expanded=True
                        ):
                            with me.box(style=me.Style(padding=me.Padding.all(16))):
                                me.markdown(state.commentary_suffix)

                elif (
                    state.prompt_response
                ):  # Fallback for completely unparsable response (no JSON, no suffix extracted)
                    me.text("Response", style=me.Style(font_weight="bold"))
                    me.box(style=me.Style(height=8))
                    with me.box(
                        style=me.Style(
                            display="grid",
                            flex_direction="row",
                            gap=5,
                            align_items="center",
                            width="100%",
                            background=BACKGROUND_COLOR,
                            border_radius=16,
                            padding=me.Padding.all(16),
                        )
                    ):
                        me.markdown(text=f"```json\n{state.prompt_response}\n```")


@me.component
def render_pydantic_response(response: ParsedChecklistResponse):
    """Renders the parsed checklist response.

    Args:
        response: The parsed checklist response.
    """
    categories_with_issues = {}
    categories_without_issues = {}

    for name, data in response.categories.items():
        if any(score for score in data.items.values()):
            categories_with_issues[name] = data
        else:
            categories_without_issues[name] = data

    # Render categories with issues first, using the card layout
    if categories_with_issues:
        me.text(
            f"Checklist found {len(categories_with_issues)} issues",
            style=me.Style(
                font_weight="bold", font_size=18, margin=me.Margin(bottom=12)
            ),
        )
        with me.box(
            style=me.Style(
                display="flex", flex_direction="row", flex_wrap="wrap", gap=16
            )
        ):
            for category_name, category_data in categories_with_issues.items():
                # Each category is a flex item
                with me.box(
                    style=me.Style(
                        flex_grow=1,
                        flex_basis="350px",  # Initial width, adjust as needed
                        min_width="300px",  # Minimum width before wrapping
                        display="flex",
                        flex_direction="column",  # Content within category box is column
                    )
                ):
                    me.text(
                        category_name.replace("_", " ").title(),
                        style=me.Style(
                            font_weight="bold", font_size=16, margin=me.Margin(bottom=8)
                        ),
                    )

                    with me.box(
                        style=me.Style(
                            background=BACKGROUND_COLOR,
                            border_radius=12,
                            padding=me.Padding.all(16),
                            height="100%",  # Make inner box fill the category card
                        )
                    ):
                        item_count = len(category_data.items)
                        for i, (item_name, score) in enumerate(
                            category_data.items.items()
                        ):
                            with me.box(style=me.Style(margin=me.Margin(bottom=8))):
                                with me.box(
                                    style=me.Style(
                                        display="flex", align_items="center", gap=8
                                    )
                                ):
                                    me.icon(
                                        "flag" if score else "check_circle",
                                        style=me.Style(
                                            color="red" if score else "green"
                                        ),
                                    )
                                    me.text(
                                        item_name.replace("_", " ").title(),
                                        style=me.Style(font_weight="medium"),
                                    )

                            if (
                                category_data.details
                                and item_name in category_data.details
                            ):
                                detail = category_data.details[item_name]
                                with me.box(
                                    style=me.Style(
                                        font_size=13,
                                        margin=me.Margin(left=32, bottom=8),
                                    )
                                ):
                                    if isinstance(detail, IssueDetail):
                                        me.markdown(f"**Issue:** {detail.issue_name}")
                                        me.markdown(
                                            f"**Location:** {detail.location_in_prompt}"
                                        )
                                        me.markdown(
                                            f"**Rationale:** {detail.rationale}"
                                        )
                                    else:
                                        # Fallback for plain string details
                                        me.markdown(str(detail))

                            if i < item_count - 1:
                                me.divider()

                        if category_data.explanation:
                            if item_count > 0:
                                me.divider()
                            me.text(
                                "Category Explanation:",
                                style=me.Style(
                                    font_weight="bold",
                                    font_size=13,
                                    margin=me.Margin(top=8, bottom=4),
                                ),
                            )
                            me.markdown(
                                str(category_data.explanation),
                                style=me.Style(font_size=13),
                            )

    # Then, render a simple list for categories without issues
    if categories_without_issues:
        me.box(style=me.Style(height=24))
        me.text(
            "The following checks passed without issues",
            style=me.Style(
                font_weight="bold", font_size=18, margin=me.Margin(bottom=12)
            ),
        )
        with me.box(
            style=me.Style(
                background=BACKGROUND_COLOR,
                border_radius=12,
                padding=me.Padding.all(16),
            )
        ):
            for category_name, category_data in categories_without_issues.items():
                with me.box(
                    style=me.Style(
                        display="flex",
                        align_items="center",
                        gap=8,
                        margin=me.Margin(bottom=8),
                    )
                ):
                    me.icon("check_circle", style=me.Style(color="green"))
                    me.text(
                        category_name.replace("_", " ").title(),
                        style=me.Style(font_weight="medium"),
                    )


@me.component
def gemini_prompt_input():
    """Renders the Gemini prompt input text area and buttons."""
    page_state = me.state(PageState)
    # ... (rest of gemini_prompt_input is unchanged)
    with me.box(
        style=me.Style(
            border_radius=16,
            padding=me.Padding.all(8),
            background=BACKGROUND_COLOR,
            display="flex",
            width="100%",
        )
    ):
        with me.box(
            style=me.Style(
                flex_grow=1,
            )
        ):
            me.native_textarea(
                autosize=True,
                min_rows=10,
                placeholder="Enter prompt to evaluate...",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background=BACKGROUND_COLOR,
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(
                        me.BorderSide(style="none"),
                    ),
                    color=me.theme_var("foreground"),
                ),
                on_blur=on_blur_prompt,
                key=str(page_state.prompt_textarea_key),
                value=page_state.prompt_placeholder,
            )
        with me.box(
            style=me.Style(
                display="flex",
                flex_direction="column",
            )
        ):
            with me.content_button(type="icon", on_click=on_click_clear_prompt):
                me.icon("clear")
            with me.content_button(type="icon", on_click=on_click_evaluate_prompt):
                me.icon("send")


def on_blur_prompt(e: me.InputBlurEvent):
    """Handles the blur event for the prompt input.

    Args:
        e: The blur event.
    """
    me.state(PageState).prompt_input = e.value


BACKGROUND_COLOR = me.theme_var("surface-container-lowest")


def on_click_evaluate_prompt(e: me.ClickEvent):
    """Handles the click event for the evaluate prompt button.

    Args:
        e: The click event.
    """
    page_state = me.state(PageState)

    if not page_state.prompt_input or not page_state.prompt_input.strip():
        print("Prompt input is empty. Evaluation skipped.")
        yield
        return

    page_state.prompt_response = ""  # Clear full response
    page_state.parsed_response_json_str = None
    page_state.commentary_suffix = None
    page_state.processing = True
    yield

    try:
        client = LLMClient()
        config = Default()
        response = client.generate_content(
            model=config.MODEL_ID,
            contents="""# Prompt for Analysis
<PROMPT>
{}
</PROMPT>
""".format(
                page_state.prompt_input
            ),
            config=GenerateContentConfig(
                system_instruction=VIDEO_PROMPT_HEALTH_CHECKLIST,
                response_modalities=["TEXT"],
            ),
        )
        response_text = response.text
        page_state.prompt_response = (
            response_text  # Store full raw response for potential fallback display
        )

        parsed_data = parse_evaluation_markdown(response_text)
        if parsed_data:
            # Sort the parsed data so that items with issues appear first
            sorted_data = dict(
                sorted(
                    parsed_data.items(),
                    key=lambda item: item[1]["items"].get("Issue Found", False),
                    reverse=True,
                )
            )
            page_state.parsed_response_json_str = json.dumps(sorted_data)
        else:
            # If no data is parsed, treat the whole response as commentary.
            page_state.commentary_suffix = response_text.strip()

    except Exception as e:
        print(f"Error processing response: {e}")
        # Fallback: treat the entire response as commentary if parsing fails.
        page_state.prompt_response = page_state.prompt_response if page_state.prompt_response else f"Error: {e}"
        page_state.commentary_suffix = page_state.prompt_response.strip()
        page_state.parsed_response_json_str = None

    page_state.processing = False
    yield


def on_click_clear_prompt(e: me.ClickEvent):
    """Handles the click event for the clear prompt button.

    Args:
        e: The click event.
    """
    state = me.state(PageState)
    state.prompt_input = ""
    state.prompt_placeholder = ""
    state.prompt_textarea_key += 1
    state.processing = False
    state.prompt_response = ""
    state.parsed_response_json_str = None
    # state.commentary_prefix = None # Prefix is no longer stored
    state.commentary_suffix = None


@me.page(
    path="/video_checklist",
    title="Promptlandia - Video Checklist",
    security_policy=me.SecurityPolicy(
        allowed_iframe_parents=["https://google.github.io"]
    ),
)
def video_page():
    """Renders the checklist page."""
    app_state = me.state(AppState)
    video_checklist_page_content(app_state)