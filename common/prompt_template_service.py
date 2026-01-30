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

"""Service for managing Prompt Templates."""

import json
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from common.metadata import db
from config.default import get_config_path


class PromptTemplate(BaseModel):
    """Data model for a single Prompt Template."""

    id: Optional[str] = None
    key: str
    label: str
    prompt: str
    category: str
    template_type: Literal["image", "text"]
    attribution: str
    is_default: bool = False
    references: Optional[list[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PromptTemplateService:
    """Service for managing Prompt Templates."""

    def __init__(self, collection_name: str = "prompt_templates"):
        self.collection_name = collection_name

    def _load_from_json(self, path: str, template_type: str) -> list[PromptTemplate]:
        """Loads a list of default templates from a JSON file."""
        templates = []
        try:
            with open(path, "r") as f:
                data = json.load(f)
                for item in data:
                    # Ensure the template matches the expected type for this context
                    if item.get("template_type") == template_type:
                        templates.append(PromptTemplate(**item, is_default=True))
        except FileNotFoundError:
            print(f"Warning: Prompt template file not found at {path}")
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {path}")
        except Exception as e:
            print(
                f"Warning: An unexpected error occurred loading templates from {path}: {e}"
            )
        return templates

    def load_templates(
        self, config_path: str, template_type: str
    ) -> list[PromptTemplate]:
        """Loads default templates from a JSON file and combines them with user-created templates from Firestore."""
        default_templates = self._load_from_json(config_path, template_type)
        user_templates = []

        # Add user-created templates from firestore
        if db:
            try:
                # Simplified query to avoid needing a composite index
                query = db.collection("prompt_templates").where(
                    "template_type", "==", template_type
                )
                for doc in query.stream():
                    try:
                        user_templates.append(PromptTemplate(**doc.to_dict(), id=doc.id))
                    except Exception as e:
                        print(
                            f"Warning: Skipping invalid prompt template from Firestore ({doc.id}): {e}"
                        )
            except Exception as e:
                # This can happen if the collection doesn't exist or indexes are missing.
                # It's not a critical error, so we just log it.
                print(f"Warning: Could not load templates from Firestore: {e}")

        # Combine and de-duplicate, giving user templates precedence
        all_templates_map = {t.key: t for t in default_templates}
        for t in user_templates:
            all_templates_map[t.key] = t

        # Sort the final list in Python
        final_list = sorted(
            all_templates_map.values(), key=lambda t: (t.category, t.label)
        )

        return final_list

    def load_all_templates(self) -> list[PromptTemplate]:
        """Loads all default and user-created templates from all sources."""
        default_templates: list[PromptTemplate] = []
        user_templates: list[PromptTemplate] = []

        # Load defaults from both files
        default_templates.extend(
            self._load_from_json(
                get_config_path("config/text_prompt_templates.json"), template_type="text"
            )
        )
        default_templates.extend(
            self._load_from_json(
                get_config_path("config/image_prompt_templates.json"), template_type="image"
            )
        )

        # Load all from Firestore
        if db:
            try:
                # Use a simple query without ordering to be more robust
                query = db.collection("prompt_templates")
                for doc in query.stream():
                    try:
                        user_templates.append(PromptTemplate(**doc.to_dict(), id=doc.id))
                    except Exception as e:
                        print(
                            f"Warning: Skipping invalid prompt template from Firestore ({doc.id}): {e}"
                        )
            except Exception as e:
                print(f"Warning: Could not load templates from Firestore: {e}")

        # Combine and de-duplicate, giving user templates precedence
        all_templates_map = {t.key: t for t in default_templates}
        for t in user_templates:
            all_templates_map[t.key] = t

        # Sort the final list in Python
        final_list = sorted(
            all_templates_map.values(), key=lambda t: (t.category, t.label)
        )
        return final_list

    def add_template(self, template: PromptTemplate) -> PromptTemplate:
        """
        Adds a new template to the Firestore collection.
        """
        if not db:
            raise ConnectionError("Firestore client is not initialized.")

        now = datetime.now(timezone.utc)
        template.created_at = now
        template.updated_at = now

        template_dict = template.model_dump(exclude_none=True)
        # Firestore does not store the ID in the document data
        template_dict.pop("id", None)

        _, doc_ref = db.collection(self.collection_name).add(template_dict)

        # Return the template with the new Firestore-generated ID
        template.id = doc_ref.id
        return template

    def update_template(self, template_id: str, updates: dict):
        """Updates an existing template in the Firestore collection."""
        if not db:
            raise ConnectionError("Firestore client is not initialized.")

        updates["updated_at"] = datetime.now(timezone.utc)

        doc_ref = db.collection(self.collection_name).document(template_id)
        doc_ref.update(updates)
        print(f"Successfully updated template '{template_id}' in Firestore.")


# Instantiate a global service object
prompt_template_service = PromptTemplateService()
