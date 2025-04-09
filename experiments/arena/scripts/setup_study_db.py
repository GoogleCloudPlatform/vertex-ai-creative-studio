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
"""Setup the study database for GenMedia Arena on Spanner."""
from typing import Optional
import fire

from config.spanner_config import ArenaStudySchema
from config.default import Default
from utils.logger import LogLevel, log

config = Default()  # Load default configuration

class ArenaStudySchemaCreationException(Exception):
    """Custom exception for errors during study database schema creation."""

def initialize_study_database(
        project_id: Optional[str] = None,
        spanner_instance_id: Optional[str] = None,
        spanner_database_id: Optional[str] = None,
):
    """Initialize the study database schema for GenMedia Arena on Spanner.
    Args:
        project_id (str): Google Cloud project ID. If None, uses default.
        spanner_instance_id (str): Spanner instance ID. If None, uses default.
        spanner_database_id (str): Spanner database ID. If None, uses default.
    Returns:
        None
    """
    if not project_id:
        project_id = config.PROJECT_ID
    if not spanner_instance_id:
        spanner_instance_id = config.SPANNER_INSTANCE_ID
    if not spanner_database_id:
        spanner_database_id = config.SPANNER_DATABASE_ID

    if not all((project_id, spanner_instance_id, spanner_database_id)):
        log(
            "Invalid input: Missing required parameters for initializing the study database schema. "
            f"Project ID: {project_id}, Spanner Instance ID: {spanner_instance_id}, "
            f"Spanner Database ID: {spanner_database_id}",
            LogLevel.ERROR
        )
        raise ArenaStudySchemaCreationException(
            "Missing required parameters for initializing the study database schema."
        )

    try:
        schema = ArenaStudySchema(
            project_id=project_id,
            spanner_instance_id=spanner_instance_id,
            spanner_database_id=spanner_database_id
        )
        schema.create_database(exists_ok=True)  # Create the database if it doesn't exist
        schema.create_schema()
    except Exception as e:
        log(
            f"Failed to initialize the study database schema: {e}",
            LogLevel.ERROR
        )
        raise ArenaStudySchemaCreationException("Failed to initialize the study database schema") from e 
    

# Entry point for the CLI application
if __name__ == "__main__":
    fire.Fire(initialize_study_database)