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
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.auth import impersonated_credentials
from google.cloud import storage
from pydantic import BaseModel

from config import default as config
from app_factory import app
from components.page_scaffold import page_scaffold
from pages.about import about_page_content
from pages.character_consistency import character_consistency_page_content
from pages.config import config_page_contents
from pages.edit_images import content as edit_images_content
from pages.gemini_tts import page as gemini_tts_page
from pages.chirp_3hd import page as chirp_3hd_page
from pages.home import home_page_content
from pages.imagen import imagen_content
from pages.library import library_content
from pages.lyria import lyria_content
from pages.portraits import motion_portraits_content
from pages.recontextualize import recontextualize
import pages.shop_the_look
from pages.test_character_consistency import page as test_character_consistency_page
from pages.gemini_image_generation import gemini_image_gen_page_content
from pages.test_index import page as test_index_page
from pages.test_infinite_scroll import test_infinite_scroll_page
from pages.test_pixie_compositor import test_pixie_compositor_page
from pages.test_uploader import test_uploader_page
from pages.test_vto_prompt_generator import page as test_vto_prompt_generator_page
from pages.test_worsfold_encoder import test_worsfold_encoder_page
from pages.veo import veo_content
from pages.vto import vto
from pages.starter_pack import page as starter_pack_page
from state.state import AppState


class UserInfo(BaseModel):
    email: str | None
    agent: str | None


# FastAPI server with Mesop
router = APIRouter()
app.include_router(router)

# Define allowed origins for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.cloudshell\.dev|http://localhost:8080",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/get_signed_url")
def get_signed_url(gcs_uri: str):
    """Generates a signed URL for a GCS object."""
    try:
        storage_client = storage.Client()
        if os.environ.get("K_SERVICE"):
            source_credentials, project = google.auth.default()
            storage_client = storage.Client(
                credentials=impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=os.environ.get("SERVICE_ACCOUNT_EMAIL"),
                    target_scopes=[
                        "https://www.googleapis.com/auth/devstorage.read_only"
                    ],
                )
            )

        bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="GET",
            service_account_email=os.environ.get("SERVICE_ACCOUNT_EMAIL"),
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
        "connect-src 'self' https://storage.mtls.cloud.google.com https://storage.googleapis.com https://*.googleusercontent.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https://storage.mtls.cloud.google.com https://storage.googleapis.com https://*.googleusercontent.com; "
        "media-src 'self' https://deepmind.google https://storage.mtls.cloud.google.com https://storage.googleapis.com https://*.googleusercontent.com; "
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

@me.page(
    path="/home",
    title="GenMedia Creative Studio - v.next",
    security_policy=me.SecurityPolicy(
        dangerously_disable_trusted_types=True,
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Google+Symbols:opsz,wght,FILL,GRAD,ROND@20..48,100..700,0..1,-50..200,0..100&icon_names=spark",
    ]
)
def home_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold(page_name="home"):  # pylint: disable=not-context-manager
        home_page_content(state)

@me.page(path="/veo", title="Veo - GenMedia Creative Studio")
def veo_page():
    with page_scaffold(page_name="veo"):
        veo_content(me.state(AppState))

@me.page(path="/motion_portraits", title="Motion Portraits - GenMedia Creative Studio")
def motion_portrait_page():
    with page_scaffold(page_name="motion_portraits"):
        motion_portraits_content(me.state(AppState))

@me.page(path="/lyria", title="Lyria - GenMedia Creative Studio")
def lyria_page():
    with page_scaffold(page_name="lyria"):
        lyria_content(me.state(AppState))

@me.page(path="/config", title="GenMedia Creative Studio - Config")
def config_page():
    with page_scaffold(page_name="config"):
        config_page_contents(me.state(AppState))

@me.page(path="/imagen", title="GenMedia Creative Studio - Imagen")
def imagen_page():
    with page_scaffold(page_name="imagen"):
        imagen_content(me.state(AppState))

@me.page(path="/library", title="GenMedia Creative Studio - Library")
def library_page():
    with page_scaffold(page_name="library"):
        library_content(me.state(AppState))

@me.page(path="/edit_images", title="GenMedia Creative Studio - Edit Images")
def edit_images_page():
    with page_scaffold(page_name="edit_images"):
        edit_images_content(me.state(AppState))

@me.page(path="/gemini-tts", title="GenMedia Creative Studio - Gemini TTS")
def gemini_tts_route():
    with page_scaffold(page_name="gemini-tts"):
        gemini_tts_page()

@me.page(path="/vto", title="GenMedia Creative Studio - Virtual Try-On")
def vto_page():
    with page_scaffold(page_name="vto"):
        vto()

@me.page(path="/starter-pack", title="GenMedia Creative Studio - Starter Pack")
def starter_pack_route():
    with page_scaffold(page_name="starter-pack"):
        starter_pack_page()

@me.page(path="/recontextualize", title="GenMedia Creative Studio - Product in Scene")
def recontextualize_page():
    with page_scaffold(page_name="recontextualize"):
        recontextualize()

@me.page(path="/character_consistency", title="GenMedia Creative Studio - Character Consistency")
def character_consistency_page():
    with page_scaffold(page_name="character_consistency"):
        character_consistency_page_content()

@me.page(path="/about", title="About - GenMedia Creative Studio")
def about_page():
    with page_scaffold(page_name="about"):
        about_page_content()


@me.page(path="/gemini_image_generation", title="Gemini Image Generation - GenMedia Creative Studio")
def gemini_image_generation_page():
    with page_scaffold(page_name="gemini_image_generation"):
        gemini_image_gen_page_content()


# Test page routes are left as is, they don't need the scaffold
me.page(path="/test_character_consistency", title="Test Character Consistency")(test_character_consistency_page)
me.page(path="/test_index", title="Test Index")(test_index_page)
me.page(path="/test_infinite_scroll", title="Test Infinite Scroll")(test_infinite_scroll_page)
me.page(path="/test_pixie_compositor", title="Test Pixie Compositor")(test_pixie_compositor_page)
me.page(path="/test_uploader", title="Test Uploader")(test_uploader_page)
me.page(path="/test_vto_prompt_generator", title="Test VTO Prompt Generator")(test_vto_prompt_generator_page)
me.page(path="/test_worsfold_encoder", title="Test Worsfold Encoder")(test_worsfold_encoder_page)


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/home")


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

