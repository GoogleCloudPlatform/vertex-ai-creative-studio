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

from pydantic import BaseModel

class PortraitStyle(BaseModel):
    id: str
    label: str
    description: str
    representative_video_gcs_uri: str

PORTRAIT_STYLES = [
    PortraitStyle(
        id="motion",
        label="Motion",
        description="The subject is in motion, with a greater detail of movement and interaction with their environment.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="distracted",
        label="Distracted",
        description="The subject appears distracted, their gaze shifting away from the camera as if something off-screen has caught their attention. They may even start to walk out of the frame.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="artistic",
        label="Artistic",
        description="The video has an artistic flair, with a focus on film grain, unique camera angles, and a non-traditional, cinematic look.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="close-up",
        label="Close-up",
        description="The camera slowly pushes in for an intimate close-up shot, focusing on the subject's facial expressions and emotions.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="selling",
        label="Selling",
        description="The subject is presenting or selling a product to the camera, holding it up, demonstrating its features, and looking persuasively at the viewer.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="podcast",
        label="Podcast",
        description="The subject is in the middle of hosting a podcast, speaking conversationally and expressively, with natural hand gestures.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="car_talking",
        label="Car Talking",
        description="The subject is filmed from the passenger seat of a car, talking to the driver (the camera) as the scenery passes by.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="mirror_selfie",
        label="Mirror Selfie",
        description="The subject is taking a video of themselves in a mirror, holding a phone and adjusting their pose and expression.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="streaming",
        label="Streaming",
        description="The subject is a streamer, sitting in a gaming chair with a headset on, reacting with excitement and intensity to something on their screen.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="catwalk",
        label="Catwalk",
        description="The subject is walking down a runway catwalk or a long hallway with confidence and style, showcasing their outfit.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="360",
        label="360",
        description="The subject does a 360 spin, showcasing their outfit.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="steadicam",
        label="Steadicam",
        description="The shot is smooth and fluid, as if filmed on a Steadicam, following the subject as they move through their environment.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="singing",
        label="Singing",
        description="The subject is passionately singing a song, with expressive facial movements and emotion, but without audible lip-sync.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
    PortraitStyle(
        id="crying",
        label="Crying",
        description="The subject is emotional and crying, capturing a moment of vulnerability and sadness with realistic tears and facial expressions.",
        representative_video_gcs_uri="gs://genai-blackbelt-fishfooding-assets/portraits/placeholder.mp4"
    ),
]
