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

import mesop as me

from state.state import AppState
from components.page_scaffold import page_scaffold
from pages.arena import arena_page_content
from pages.leaderboard import leaderboard_page_content
from pages.history import history_page_content
from pages.settings import settings_page_content

# from pages.gemini2 import gemini_page_content


def on_load(e: me.LoadEvent):  # pylint: disable=unused-argument
    """On load event"""
    #print("load event", e) # this event looks like: LoadEvent(path='/') or LoadEvent(path='/leaderboard')
    s = me.state(AppState)
    print("theme", s.theme_mode)
    if s.theme_mode:  # recall state theme mode
        me.set_theme_mode(s.theme_mode)
    else:
        me.set_theme_mode("system")


@me.page(
    path="/",
    title="Arena - Home",
    on_load=on_load,
    security_policy=me.SecurityPolicy(dangerously_disable_trusted_types=True),
)
def home_page():
    """Main Page"""
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        arena_page_content(state)


@me.page(
    path="/leaderboard",
    title="Arena - Leaderboard",
    on_load=on_load,
    security_policy=me.SecurityPolicy(dangerously_disable_trusted_types=True),
)
def leaderboard_page():
    """Leaderboard Page"""
    leaderboard_page_content(me.state(AppState))


@me.page(
    path="/history",
    title="Arena - History",
    on_load=on_load,
    security_policy=me.SecurityPolicy(dangerously_disable_trusted_types=True),
)
def history_page():
    """History Page"""
    history_page_content(me.state(AppState))
    

@me.page(
    path="/settings",
    title="Arena - Settings",
    on_load=on_load,
    security_policy=me.SecurityPolicy(dangerously_disable_trusted_types=True),
)
def settings_page():
    """Another Page"""
    settings_page_content(me.state(AppState))


# @me.page(
#     path="/gemini",
#     title="Scaffold - Gemini",
#     on_load=on_load,
# )
# def gemini_page():
#     """Gemini 2.0 Flash Page"""
#     state = me.state(AppState)
#     with page_scaffold():  # pylint: disable=not-context-manager
#         gemini_page_content(state)
