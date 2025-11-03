# Copyright 2024 Google LLC
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

"""Python wrapper for the Scroll Sentinel Lit component."""

import mesop as me
import typing


@me.web_component(path="./scroll_sentinel.js")
def scroll_sentinel(
    *,
    on_visible: typing.Callable[[me.WebEvent], None],
    is_loading: bool,
    all_items_loaded: bool,
    key: str | None = None,
):
    """Defines the API for the scroll_sentinel web component."""
    return me.insert_web_component(
        key=key,
        name="scroll-sentinel",
        properties={
            "isLoading": is_loading,
            "allItemsLoaded": all_items_loaded,
        },
        events={
            "visible": on_visible,
        },
    )
