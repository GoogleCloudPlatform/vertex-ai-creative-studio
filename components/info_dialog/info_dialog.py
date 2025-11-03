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

"""A reusable component for displaying page information dialogs."""

from typing import Callable

import mesop as me

from components.dialog import dialog


@me.component
def info_dialog(
    is_open: bool,
    info_data: dict | None,
    on_close: Callable[[me.ClickEvent], None],
    default_title: str = "About This Page",
):
    """This is a reusable, safe-rendering dialog for displaying page information.

    Args:
        is_open: Whether the dialog should be currently open.
        info_data: A dictionary containing 'title' and 'description' keys. Can be None.
        on_close: The event handler to call when the close button is clicked.
        default_title: The title of the page to use in the dialog header.
    """
    print(f"DEBUG: info_dialog component rendering, is_open = {is_open}")
    # Always render the underlying dialog component and pass `is_open` to it.
    # The dialog component itself will handle its visibility.
    with dialog(is_open=is_open):
        title = default_title
        description = "Information for this page has not been configured yet. Please add an entry to `config/about_content.json`."

        if info_data:
            title = f"About {info_data.get('title', 'Untitled')}"
            description = info_data.get(
                "description",
                "No description is available.",
            )

        me.text(title, type="headline-6")
        me.markdown(description)
        me.divider()
        with me.box(style=me.Style(margin=me.Margin(top=16))):
            me.button("Close", on_click=on_close, type="flat")
