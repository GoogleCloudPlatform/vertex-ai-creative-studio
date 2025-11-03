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

from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import List, Optional


class GeneratedImageAccuracy(BaseModel):
    """Pydantic model for the best image selection."""

    article_image_path: str
    reasoning: str
    best_image: bool
    accurate: bool


class GeneratedImageAccuracyWrapper(BaseModel):
    """Pydantic model for the best image selection."""

    image_accuracy: list[GeneratedImageAccuracy]
    accurate: bool
    reasoning: str


class BestImageAccuracy(BaseModel):
    """Pydantic model for the best image selection."""

    image_accuracy: list[GeneratedImageAccuracy]
    accurate: bool
    reasoning: str


@dataclass
class CatalogRecord:
    item_id: str = None
    article_type: str = None
    model_group: str = None
    ai_description: str = None
    selected: bool = False
    available_to_select: bool = True
    clothing_image: str = None
    upload_user: str = None
    timestamp: str = None


class ArticleDescription(BaseModel):
    """Pydantic model for the best image selection."""

    article_image_path: str
    article_description: str


class ArticleDescriptionWrapper(BaseModel):
    """Pydantic model for the best image selection."""

    articles: list[ArticleDescription]
    look_description: str


@dataclass
class ModelRecord:
    model_group: str = None
    model_id: str = None
    model_image: str = None
    primary_view: bool = True
    upload_user: str = None
    timestamp: str = None


@dataclass
class ProgressionImage:
    image_path: str = None  # progression image
    best_image: bool = None
    reasoning: str = None
    # critic_result: CriticResult = None
    article_image_path: str = None
    reasoning: str = None
    best_image: bool = False
    accurate: bool = False


@dataclass
class ProgressionImages:
    progression_images: list[ProgressionImage] = None
