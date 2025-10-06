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
"""Main Mesop App."""

import datetime
import inspect
import os
import uuid

import google.auth
import mesop as me
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.auth import impersonated_credentials
from google.cloud import storage
from pydantic import BaseModel

import pages.shop_the_look
from app_factory import app
from common.utils import gcs_uri_to_https_url
from components.page_scaffold import page_scaffold
from config import default as config
from models.video_processing import convert_mp4_to_gif
from pages import about as about_page
from pages import character_consistency as character_consistency_page
from pages import chirp_3hd as chirp_3hd_page
from pages import config as config_page
from pages import gemini_image_generation as gemini_image_generation_page
from pages import gemini_tts as gemini_tts_page
from pages import home as home_page
from pages import imagen as imagen_page
from pages.library_v2 import page as library_v2_page
from pages.legacy_library import page as legacy_library_page
from pages import lyria as lyria_page
from pages import portraits as motion_portraits
from pages import recontextualize as recontextualize_page
from pages import starter_pack as starter_pack_page
from pages import veo
from pages import vto as vto_page
from pages import interior_design_v2 as interior_design_page
from pages import welcome as welcome_page
from pages.edit_images import content as edit_images_content
from pages.test_character_consistency import page as test_character_consistency_page
from pages.test_index import page as test_index_page
from pages.test_infinite_scroll import test_infinite_scroll_page
from pages.test_pixie_compositor import test_pixie_compositor_page
from pages.test_uploader import test_uploader_page
from pages.test_vto_prompt_generator import page as test_vto_prompt_generator_page
from pages.test_worsfold_encoder import test_worsfold_encoder_page
from pages.test_svg import test_svg_page
from pages.test_media_chooser import page as test_media_chooser_page
from pages import pixie_compositor as pixie_compositor_page
from state.state import AppState
import google.auth

class UserInfo(BaseModel):
    email: str | None
    agent: str | None


# FastAPI server with Mesop
router = APIRouter()
app.include_router(router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("assets/favicon.ico")

# Define allowed origins for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.cloudshell\.dev|http://localhost:8080",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/convert_to_gif")
def convert_to_gif(gcs_uri: str, request: Request):
    """Converts an MP4 video to a GIF and saves it to GCS."""
    try:
        uri = convert_mp4_to_gif(gcs_uri, request.scope["MESOP_USER_EMAIL"])

        return {"url": gcs_uri_to_https_url(uri)}
    except Exception as e:
        error_message = str(e)
        print(f"Error generating GIF: {error_message}")
        return {"error": error_message}, 500

@app.get("/api/get_signed_url")
def get_signed_url(gcs_uri: str):
    """Generates a signed URL for a GCS object."""
    try:
        credentials, _ = google.auth.default()

        signing_credentials = impersonated_credentials.Credentials(
            source_credentials=credentials,
            target_principal=config.Default.SERVICE_ACCOUNT_EMAIL,
            target_scopes="https://www.googleapis.com/auth/devstorage.read_only",
        )

        storage_client = storage.Client()
        bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="GET",
            credentials=signing_credentials
        )

        return {"signed_url": signed_url}
    except Exception as e:
        error_message = str(e)
        print(f"Error generating signed url: {error_message}")
        if "private key" in error_message:
            print(
                "This error often occurs in a local development environment. "
                "Please ensure you have authenticated with service account impersonation by running: "
                "gcloud auth application-default login --impersonate-service-account=<YOUR_SERVICE_ACCOUNT_EMAIL>"
            )
        return {"error": error_message}, 500


@app.middleware("http")
async def add_global_csp(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://esm.sh https://cdn.jsdelivr.net; "
        "connect-src 'self' https://esm.sh https://storage.cloud.google.com https://storage.googleapis.com https://*.googleusercontent.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https://google-ai-skin-tone-research.imgix.net https://storage.cloud.google.com https://storage.googleapis.com https://*.googleusercontent.com; "
        "media-src 'self' https://deepmind.google https://storage.cloud.google.com https://storage.googleapis.com https://*.googleusercontent.com; "
        "worker-src 'self' blob:;"
    )
    return response


@app.middleware("http")
async def set_request_context(request: Request, call_next):
    user_email = request.headers.get("X-Goog-Authenticated-User-Email")
    if not user_email:
        user_email = "anonymous@google.com"
    if user_email.startswith("accounts.google.com:"):
        user_email = user_email.split(":")[-1]

    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    request.scope["MESOP_USER_EMAIL"] = user_email
    request.scope["MESOP_SESSION_ID"] = session_id

    # Pass GA ID to Mesop context if it exists
    if config.Default.GA_MEASUREMENT_ID:
        request.scope["MESOP_GA_MEASUREMENT_ID"] = config.Default.GA_MEASUREMENT_ID

    response = await call_next(request)
    response.set_cookie(
        key="session_id", value=session_id, httponly=True, samesite="Lax"
    )
    return response


# Test page routes are left as is, they don't need the scaffold
me.page(path="/test_character_consistency", title="Test Character Consistency")(
    test_character_consistency_page
)
me.page(path="/test_index", title="Test Index")(test_index_page)
me.page(path="/test_infinite_scroll", title="Test Infinite Scroll")(
    test_infinite_scroll_page
)
me.page(path="/test_pixie_compositor", title="Test Pixie Compositor")(
    test_pixie_compositor_page
)
me.page(path="/test_uploader", title="Test Uploader")(test_uploader_page)
me.page(path="/test_vto_prompt_generator", title="Test VTO Prompt Generator")(
    test_vto_prompt_generator_page
)
me.page(path="/test_worsfold_encoder", title="Test Worsfold Encoder")(
    test_worsfold_encoder_page
)
me.page(path="/test_svg", title="Test SVG")(
    test_svg_page
)
me.page(path="/test_media_chooser", title="Test Media Chooser")(
    test_media_chooser_page
)


@app.get("/")
def root_redirect(request: Request) -> RedirectResponse:
    """Redirects to /welcome for first-time users, otherwise to /home."""
    # Check if our tracking cookie exists on the incoming request.
    if request.cookies.get("has_visited_welcome"):
        # If it does, send the user to the regular home page.
        return RedirectResponse(url="/home")
    else:
        # If it doesn't, it's a first-time visit.
        # Create a response that will send the user to the welcome page.
        response = RedirectResponse(url="/welcome")

        # Before sending the response, set our cookie on it.
        # The browser will save this cookie for future visits.
        # max_age=31536000 sets the cookie to expire in 1 year.
        # max_age=172800 sets the cookie to expire in 48 hours.
        response.set_cookie(
            key="has_visited_welcome",
            value="true",
            max_age=172800,
            httponly=True,
        )
        return response


# Use this to mount the static files for the Mesop app
app.mount(
    "/__web-components-module__",
    StaticFiles(directory="."),
    name="web_components",
)
app.mount(
    "/static",
    StaticFiles(
        directory=os.path.join(
            os.path.dirname(inspect.getfile(me)),
            "web",
            "src",
            "app",
            "prod",
            "web_package",
        )
    ),
    name="static",
)

app.mount(
    "/assets",
    StaticFiles(directory="assets"),
    name="assets",
)



app.mount(
    "/",
    WSGIMiddleware(
        me.create_wsgi_app(debug_mode=os.environ.get("DEBUG_MODE", "") == "true")
    ),
)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        reload_includes=["*.py", "*.js"],
        timeout_graceful_shutdown=0,
        proxy_headers=True,
    )