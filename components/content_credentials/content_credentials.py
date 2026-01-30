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

@me.web_component(path="./content_credentials.js")
def content_credentials_viewer(
    *,
    manifest: str, # Expecting JSON string
    key: str | None = None,
):
    """
    A web component that displays Content Credentials (C2PA) data.
    
    Args:
        manifest: The parsed C2PA manifest as a JSON string.
    """
    if not manifest:
        return
        
    return me.insert_web_component(
        key=key,
        name="content-credentials-viewer",
        properties={
            "manifestJson": manifest,
        },
    )