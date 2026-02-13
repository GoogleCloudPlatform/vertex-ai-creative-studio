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

import time
import mesop as me
import requests
from dataclasses import dataclass, field
from models.requests import VideoGenerationRequest
from common.utils import create_display_url

@me.stateclass
@dataclass
class AsyncVeoState:
    prompt: str = "A cute puppy playing in a field of flowers"
    job_id: str = ""
    job_status: str = ""
    video_uri: str = ""
    error_message: str = ""
    is_loading: bool = False

@me.page(path="/test_async_veo", title="Test Async Veo")
def page():
    state = me.state(AsyncVeoState)

    with me.box(style=me.Style(padding=me.Padding.all(20), display="flex", flex_direction="column", gap=20)):
        me.text("Async Veo Generation Test", type="headline-4")

        me.textarea(
            label="Prompt",
            value=state.prompt,
            on_blur=on_prompt_blur,
            style=me.Style(width="100%"),
        )

        me.button(
            "Generate Async",
            on_click=on_click_generate,
            type="flat",
            disabled=state.is_loading,
        )

        if state.job_id:
            me.text(f"Job ID: {state.job_id}")
            me.text(f"Status: {state.job_status}")

        if state.is_loading:
            me.progress_spinner()

        if state.video_uri:
            me.video(
                src=create_display_url(state.video_uri),
                style=me.Style(width="100%", max_width=640),
            )

        if state.error_message:
            me.text(f"Error: {state.error_message}", style=me.Style(color="red"))


def on_prompt_blur(e: me.InputBlurEvent):
    state = me.state(AsyncVeoState)
    state.prompt = e.value

def on_click_generate(e: me.ClickEvent):
    state = me.state(AsyncVeoState)
    state.is_loading = True
    state.job_id = ""
    state.job_status = "starting..."
    state.video_uri = ""
    state.error_message = ""
    yield

    # 1. Call Async Endpoint
    try:
        # We need the base URL. In Mesop, we can often use relative paths if served from same origin.
        # Assuming the app is running on localhost:8080 for dev.
        # A better way might be to find the host dynamically if possible, but relative path should work for fetch.
        # Since we are in python, we need the full URL if using requests, OR we use a relative path if we are in browser.
        # Mesop runs on the server, so 'requests' needs the full URL of the FastAPI app.
        # Assuming standard dev port 8080.
        api_url = "http://localhost:8080/api/veo/generate_async"
        
        # Construct a minimal valid request
        request_data = VideoGenerationRequest(
            prompt=state.prompt,
            model_version_id="2.0", # Hardcoded for test
            aspect_ratio="16:9",
            duration_seconds=5,
            resolution="720p",
            video_count=1,
            enhance_prompt=False,
            generate_audio=False,
            person_generation="Allow (Adults only)",
        )
        
        # We need to pass the user email header for auth middleware to work
        headers = {"X-Goog-Authenticated-User-Email": "test_user@example.com"}
        
        response = requests.post(api_url, json=request_data.model_dump(), headers=headers)
        response.raise_for_status()
        data = response.json()
        state.job_id = data["job_id"]
        state.job_status = data["status"]
        yield
    except Exception as e:
        state.error_message = f"Failed to start job: {e}"
        state.is_loading = False
        yield
        return

    # 2. Poll for Status
    while state.job_status in ["pending", "processing", "created"]:
        time.sleep(2) # Simple polling sleep
        try:
            status_url = f"http://localhost:8080/api/veo/job/{state.job_id}"
            resp = requests.get(status_url)
            resp.raise_for_status()
            status_data = resp.json()
            state.job_status = status_data["status"]
            
            if state.job_status == "complete":
                state.video_uri = status_data["video_uri"]
                state.is_loading = False
            elif state.job_status == "failed":
                state.error_message = status_data.get("error_message", "Unknown error")
                state.is_loading = False
            
            yield
        except Exception as e:
            state.error_message = f"Polling failed: {e}"
            state.is_loading = False
            yield
            break
