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

import typing

import mesop as me


@me.web_component(path="/components/drawing/image_drawer.js")
def image_drawer(
    *,
    image_url: str,
    pen_color: str,
    pen_width: int,
    on_save: typing.Callable[[me.WebEvent], None] | None = None,
    key: str | None = None,
):
    """Defines the API for the image drawing web component."""
    return me.insert_web_component(
        key=key,
        name="image-drawer",
        properties={
            "imageUrl": image_url,
            "penColor": pen_color,
            "penWidth": pen_width,
        },
        events={
            "saveEvent": on_save,
        },
    )
