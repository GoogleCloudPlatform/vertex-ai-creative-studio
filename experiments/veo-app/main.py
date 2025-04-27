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
"""Main Mesop App"""

import os

import mesop as me
from components.page_scaffold import page_scaffold
from fastapi import APIRouter, FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from pages.config import config_page_contents
from pages.home import home_page_content
from pages.imagen import imagen_content
from pages.library import library_content
from pages.lyria import lyria_content
from pages.portraits import motion_portraits_content
from pages.veo import veo_content
from state.state import AppState

# from pages.gemini2 import gemini_page_content


def on_load(e: me.LoadEvent):  # pylint: disable=unused-argument
    """On load event"""
    s = me.state(AppState)
    if s.theme_mode:
        if s.theme_mode == "light":
            me.set_theme_mode("light")
        elif s.theme_mode == "dark":
            me.set_theme_mode("dark")
    else:
        me.set_theme_mode("system")
        s.theme_mode = me.theme_brightness()


@me.page(
    path="/",
    title="GenMedia Creative Studio - Veo 2",
    on_load=on_load,
)
def home_page():
    """Main Page"""
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        home_page_content(state)


@me.page(
    path="/veo",
    title="Veo 2 - GenMedia Creative Studio",
    on_load=on_load,
)
def veo_page():
    """Veo Page"""
    veo_content(me.state(AppState))


@me.page(
    path="/motion_portraits",
    title="Motion Portraits - GenMedia Creative Studio",
    on_load=on_load,
)
def motion_portrait_page():
    """Motion Portrait Page"""
    motion_portraits_content(me.state(AppState))


@me.page(
    path="/lyria",
    title="Lyria - GenMedia Creative Studio",
    on_load=on_load,
)
def lyria_page():
    """Lyria Page"""
    lyria_content(me.state(AppState))


@me.page(
    path="/config",
    title="GenMedia Creative Studio - Config",
    on_load=on_load,
)
def config_page():
    """Config Page"""
    config_page_contents(me.state(AppState))


@me.page(
    path="/imagen",
    title="GenMedia Creative Studio - Imagen",
    on_load=on_load,
)
def imagen_page():
    """Imagen Page"""
    imagen_content(me.state(AppState))


@me.page(
    path="/library",
    title="GenMedia Creative Studio - Library",
    on_load=on_load,
)
def library_page():
    """Library Page"""
    library_content(me.state(AppState))


# FastAPI server with Mesop
app = FastAPI()
router = APIRouter()
app.include_router(router)


@app.get("/hello")
def hello():
    return "world"


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
