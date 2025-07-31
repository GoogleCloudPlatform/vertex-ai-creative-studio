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

import inspect
import os
import uuid

import google.auth
import mesop as me
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google.cloud import storage
import datetime

from app_factory import app
from components.page_scaffold import page_scaffold
from pages.character_consistency import character_consistency_page_content
from pages.config import config_page_contents
from pages.edit_images import content as edit_images_content
from pages.home import home_page_content
from pages.imagen import imagen_content
from pages.library import library_content
from pages.lyria import lyria_content
from pages.portraits import motion_portraits_content
from pages.recontextualize import recontextualize
from pages.test_uploader import test_uploader_page
from pages.test_infinite_scroll import test_infinite_scroll_page
from pages.veo import veo_content
from pages.vto import vto
from pages.about import about_page_content
from pages.doodle import doodle_page
from state.state import AppState


class UserInfo(BaseModel):
    email: str | None
    agent: str | None


# FastAPI server with Mesop
router = APIRouter()
app.include_router(router)


@app.middleware("http")
async def set_request_context(request: Request, call_next):
    """
    Sets request-scoped context for both FastAPI and Mesop.
    
    This middleware performs the following actions:
    1.  Retrieves the user's email from the 'X-Goog-Authenticated-User-Email' header,
        with a fallback for local development.
    2.  Retrieves the session ID from the 'session_id' cookie or creates a new one.
    3.  Stores the user email and session ID in 'request.scope' for the WSGI middleware
        to pass to the Mesop application.
    """
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

    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://esm.sh; object-src 'none'; base-uri 'self'; trusted-types angular angular#unsafe-bypass lit-html highlight.js;"
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite='Lax')
    return response


@me.page(
    path="/home",
    title="GenMedia Creative Studio - v.next",
)
def home_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        home_page_content(state)


@me.page(
    path="/veo",
    title="Veo - GenMedia Creative Studio",
)
def veo_page():
    """Veo Page."""
    veo_content(me.state(AppState))


@me.page(
    path="/motion_portraits",
    title="Motion Portraits - GenMedia Creative Studio",
)
def motion_portrait_page():
    """Motion Portrait Page."""
    motion_portraits_content(me.state(AppState))


@me.page(
    path="/lyria",
    title="Lyria - GenMedia Creative Studio",
)
def lyria_page():
    """Lyria Page."""
    lyria_content(me.state(AppState))


@me.page(
    path="/config",
    title="GenMedia Creative Studio - Config",
)
def config_page():
    """Config Page."""
    config_page_contents(me.state(AppState))


@me.page(
    path="/imagen",
    title="GenMedia Creative Studio - Imagen",
    security_policy=me.SecurityPolicy(
        allowed_script_srcs=[
            "https://cdn.jsdelivr.net",
        ],
        dangerously_disable_trusted_types=True,
    ),
)
def imagen_page():
    """Imagen Page."""
    imagen_content(me.state(AppState))


@me.page(
    path="/library",
    title="GenMedia Creative Studio - Library",
)
def library_page():
    """Library Page."""
    library_content(me.state(AppState))


@me.page(
    path="/edit_images",
    title="GenMedia Creative Studio - Edit Images",
)
def edit_images_page():
    """Edit Images Page."""
    edit_images_content(me.state(AppState))


@me.page(
    path="/vto",
    title="GenMedia Creative Studio - Virtual Try-On",
)
def vto_page():
    """VTO Page"""
    vto()


@me.page(
    path="/recontextualize",
    title="GenMedia Creative Studio - Product in Scene",
)
def recontextualize_page():
    """Recontextualize Page"""
    recontextualize()


@me.page(
    path="/character_consistency",
    title="GenMedia Creative Studio - Character Consistency",
)
def character_consistency_page():
    """Character Consistency Page"""
    character_consistency_page_content()


@me.page(
    path="/about",
    title="About - GenMedia Creative Studio",
)
def about_page():
    """About Page"""
    about_page_content()


@me.page(
    path="/doodle",
    title="Doodle Pad - GenMedia Creative Studio",
)
def doodle_page_entry():
    """Doodle Page Entry Point"""
    doodle_page()


@app.get("/api/get_signed_url")
def get_signed_url(gcs_uri: str):
    """Generates a signed URL for a GCS object."""
    storage_client = storage.Client()
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
    )