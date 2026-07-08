# Copyright 2026 Google LLC
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

"""Mesop web component wrapper for direct GCS file uploads via Signed URLs."""

from typing import Callable

import mesop as me


@me.web_component(path="./gcs_uploader.js")
def gcs_uploader(  # noqa: PLR0913, ANN201
    *,
    signed_url: str = "",
    gcs_uri: str = "",
    accepted_file_types: list[str] | None = None,
    disabled: bool = False,
    label: str = "Upload File",
    on_request_signed_url: Callable[[me.WebEvent], object],
    on_upload_complete: Callable[[me.WebEvent], object],
    on_upload_progress: Callable[[me.WebEvent], object],
    on_upload_error: Callable[[me.WebEvent], object],
    key: str | None = None,
):
    """Render a button to directly upload files to GCS via browser signed URLs."""
    if accepted_file_types is None:
        accepted_file_types = ["video/mp4"]

    return me.insert_web_component(
        key=key,
        name="gcs-uploader",
        properties={
            "signedUrl": signed_url,
            "gcsUri": gcs_uri,
            "acceptedFileTypes": accepted_file_types,
            "disabled": disabled,
            "label": label,
        },
        events={
            "requestSignedUrl": on_request_signed_url,
            "uploadComplete": on_upload_complete,
            "uploadProgress": on_upload_progress,
            "uploadError": on_upload_error,
        },
    )
