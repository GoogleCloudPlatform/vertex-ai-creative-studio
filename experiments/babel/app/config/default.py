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

import os
from dataclasses import dataclass, field
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv(override=True)


class Voice(TypedDict):
    """Voice definition"""

    name: str
    gender: str
    language_codes: list[str]


class BabelMetadata(TypedDict):
    """Babel response metadata definition"""

    voice_name: str
    language_code: str
    gender: str
    text: str
    audio_path: str


@dataclass
class Default:
    """Default definition"""

    PROJECT_ID: str = os.environ.get("PROJECT_ID")
    LOCATION: str = os.environ.get("LOCATION", "us-central1")
    GENMEDIA_BUCKET: str = os.environ.get(
        "GENMEDIA_BUCKET", f"{PROJECT_ID}-fabulae/babel"
    )  # without the "gs://"
    MODEL_ID: str = os.environ.get("MODEL_ID", "gemini-3.5-flash")
    BABEL_ENDPOINT: str = os.environ.get(
        "BABEL_ENDPOINT", "http://localhost:8080"
    )  # defaults to # "http://localhost:8080"
    STATIC_PUBLIC_BUCKET: str = "github-repo/audio_ai/audio_generation/chirp3_hd_babel"

    voices: list[Voice] = field(default_factory=lambda: [])


gemini_voices = [
    "Zephyr",
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Leda",
    "Orus",
    "Aoede",
]


reference_voices = [
    {"name": "Zephyr"},
    {"name": "Kore"},
    {"name": "Puck"},
    {"name": "Charon"},
    {"name": "Fenrir"},
    {"name": "Orus"},
    {"name": "Aoede"},
    {"name": "Leda"},
]
