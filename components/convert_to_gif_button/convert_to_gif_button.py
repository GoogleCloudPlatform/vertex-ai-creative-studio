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

"""Python wrapper for the Convert to GIF Lit component."""
import mesop as me

@me.web_component(path="./convert_to_gif_button.js")
def convert_to_gif_button(
    *,
    # --- Properties ---
    url: str = "",
    filename: str = "",
    key: str | None = None,
):
    """Defines the API for the Convert to GIF web component."""
    return me.insert_web_component(
        key=key,
        name="convert-to-gif-button",
        properties={
            "url": url,
            "filename": filename,
        },
    )
