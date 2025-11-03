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
import typing


@me.web_component(path="./infinite_scroll_library.js")
def infinite_scroll_library(
    *,
    items: list[dict],
    has_more_items: bool,
    on_load_more: typing.Callable[[me.WebEvent], None],
    on_image_selected: typing.Callable[[me.WebEvent], None],
    key: str | None = None,
):
  """
  A web component for displaying a library of images with infinite scroll.
  """
  return me.insert_web_component(
    key=key,
    name="infinite-scroll-library",
    properties={
        "items": items,
        "hasMoreItems": has_more_items,
    },
    events={
        "loadMoreEvent": on_load_more,
        "imageSelectedEvent": on_image_selected,
    },
  )