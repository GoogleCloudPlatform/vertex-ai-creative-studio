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

"""Tests for the character consistency test page."""

# ruff: noqa: S101

from pages.test_character_consistency import (
    PageState,
    _default_selected_image_url,
)


def test_default_selected_image_prefers_user_selection() -> None:
    """Uses an explicit user selection before any generated default."""
    state = PageState()
    state.user_selected_image_url = "/media/bucket/manual.png"
    state.best_image_url = "/media/bucket/best.png"
    state.candidate_image_urls = ["/media/bucket/first.png"]

    assert _default_selected_image_url(state) == "/media/bucket/manual.png"


def test_default_selected_image_uses_best_image() -> None:
    """Uses the model-selected image when the user did not choose one."""
    state = PageState()
    state.best_image_url = "/media/bucket/best.png"
    state.candidate_image_urls = ["/media/bucket/first.png"]

    assert _default_selected_image_url(state) == "/media/bucket/best.png"


def test_default_selected_image_uses_first_candidate_without_best() -> None:
    """Falls back to the first candidate only when no best image is set."""
    state = PageState()
    state.candidate_image_urls = [
        "/media/bucket/first.png",
        "/media/bucket/second.png",
    ]

    assert _default_selected_image_url(state) == "/media/bucket/first.png"
