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
"""Spanner table creation script: tables and indexes used by the Arena Study."""

# Prerequisite: Create a Spanner instance "arena_study" on GCP console with 100 processing units.
from dataclasses import dataclass, field, fields
import dataclasses
from datetime import datetime
from enum import Enum
import logging
import secrets
import string
from typing import Optional

from google.cloud import spanner

from utils.logger import LogLevel, log
from config.default import Default


config = Default()

@dataclass
class ArenaModelEvaluation():
    """This class maps 1:1 to DB table 'Study'. IO is handled by Spanner ORM."""
    model_name: str = field(default=None)  # Default model name if not provided
    study: str = field(default=None)  # Default study name if not provided
    time_of_rating: datetime | None = field(default=None)  # Time of rating
    rating: float = field(default=1000.0)  # Default rating is 1000.0 if not provided
    id: str = field(default_factory=lambda: '')  # Unique identifier for the study run

    def __post_init__(self):
        if not isinstance(self.model_name, str) or not self.model_name:
            raise ValueError("model_name must be a non-empty string.")
        if self.time_of_rating is not None and not isinstance(self.time_of_rating, datetime):
            raise ValueError("time_of_rating must be a datetime object.")
        if not isinstance(self.rating, (float, int)):
            raise ValueError("rating must be a float or int.")
        if not isinstance(self.study, str) or not self.study:
            raise ValueError("study must be a non-empty string.")
        if not isinstance(self.id, str):
            raise ValueError("id must be a string.")
        log(f"Initialized StudyRun: {self.model_name}, {self.time_of_rating}, {self.rating}, {self.study}, {self.id}")

class ArenaStudyTracker:
    """Arena Study Tracker for managing study runs in Spanner (Singleton)."""

    _instance = None

    def __new__(cls, project_id: str, spanner_instance_id: str, spanner_database_id: str):
        if cls._instance is None:
            cls._instance = super(ArenaStudyTracker, cls).__new__(cls)
            cls._instance.project_id = project_id
            cls._instance.spanner_instance_id = spanner_instance_id
            cls._instance.spanner_database_id = spanner_database_id
            cls._instance.client = spanner.Client(project=project_id)
            cls._instance.instance = cls._instance.client.instance(spanner_instance_id)
            cls._instance.database = cls._instance.instance.database(spanner_database_id)
            log("ArenaStudyTracker instance created.")
        return cls._instance

    def _generate_unique_id(self, number_characters: int = 8) -> str:
        """Generate a unique ID of a specified length."""
        characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
        unique_id = ''.join(secrets.choice(characters) for _ in range(number_characters))
        log(f"Generated unique ID: {unique_id}")
        return unique_id

    def upsert_study_runs(self, study_runs: list[ArenaModelEvaluation], table_name: Optional[str] = "Study"):
        """Adds or updates a list of study runs in the Spanner database."""
        inserts = []
        updates = []
        
        current_timestamp = spanner.COMMIT_TIMESTAMP
        for study_run in study_runs:
            is_insert = False
            if not study_run.id:
                study_run.id = self._generate_unique_id()
                is_insert = True
            if not study_run.time_of_rating:
                study_run.time_of_rating = current_timestamp
                is_insert = True
                log("Setting time_of_rating to commit timestamp as it was not provided.")

            columns = [field.name for field in fields(ArenaModelEvaluation)]
            values = []
            for field in fields(ArenaModelEvaluation):
                value = getattr(study_run, field.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                if isinstance(value, Enum):
                    value = str(value)
                values.append(value)

            if is_insert:
                inserts.append(values)
            else:
                updates.append(values)

        try:
            with self.database.batch() as batch:
                if inserts:
                    log(f"Inserting {len(inserts)} new study runs into the database.")
                    batch.insert(table_name, columns=columns, values=inserts)
                if updates:
                    log(f"Updating {len(updates)} existing study runs in the database.")
                    batch.update(table_name, columns=columns, values=updates)
            log(f"{len(study_runs)} study runs added/updated successfully in the database.")
        except Exception as e:
            raise Exception(f"Error adding study runs: {e}") from e
        finally:
            self._close_connection()

    def close(self):
        """Close the Spanner client connection."""
        self._close_connection()

    def _close_connection(self):
        """Internal method to close the Spanner client connection."""
        if self._instance and self._instance.client:
            self._instance.client.close()
            self._instance.client = None
            log("Database connection closed.")
        else:
            log("Client was already closed or not initialized.", LogLevel.WARNING)

    def __del__(self):
        """Destructor to ensure the Spanner client is closed when the object is deleted."""
        self.close()
        log("ArenaStudyTracker instance deleted and database connection closed.")

    def __enter__(self):
        """Enter the runtime context for the ArenaStudyTracker."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context for the ArenaStudyTracker and close the client."""
        self.close()
        if exc_type:
            log(f"Exception occurred: {exc_value}", LogLevel.ERROR)
        return False
 
class ArenaStudySchema():
    """Arena Study Schema"""

    def __init__(self, project_id: str, spanner_instance_id: str, spanner_database_id: str):
        self.project_id = project_id
        self.spanner_instance_id = spanner_instance_id
        self.spanner_database_id = spanner_database_id
        self.client = spanner.Client(project_id)
        self.instance = self.client.instance(self.spanner_instance_id)
        self.database = self.instance.database(self.spanner_database_id)
    
    def create_database(self, exists_ok: bool = False):
        """Create Spanner database if it does not exist."""
        try:
            operation = self.database.create()
            # Wait for the operation to complete
            log(f"Creating database {self.spanner_database_id}.")
            log(f"Adding to Spanner instance {self.spanner_instance_id} in project {self.project_id}.")
            operation.result(config.SPANNER_TIMEOUT)
            log("Database created successfully.")
        except Exception as e:
            if "Database already exists" in str(e) and exists_ok:
                log("Database already exists, skipping creation.")
                return
            raise Exception(f"Error creating database: {e}") from e 

    def create_study_table(self):
        """Create study table"""
        try:
            log("Creating study table.")
            operation = self.database.update_ddl([
                """
                CREATE TABLE Study (
                    model_name STRING(MAX) NOT NULL,
                    time_of_rating TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                    rating FLOAT64 NOT NULL,
                    study STRING(MAX) NOT NULL,
                    id STRING(MAX) NOT NULL
                )
                PRIMARY KEY (study, model_name, time_of_rating)
                """])
            operation.result(config.SPANNER_TIMEOUT)
            log("Study table created successfully.")
        except Exception as e:
            raise Exception(f"Error creating study table: {e}") from e
    
    def create_study_index(self):
        """Create study index"""
        try:
            log("Creating study index.")
            # To query ratings for a specific model across all studies
            operation = self.database.update_ddl([
                """
                CREATE INDEX StudyByModel ON Study(model_name)
                """
            ])
            operation.result(config.SPANNER_TIMEOUT)
            log("Study index created successfully.")
        except Exception as e:
            raise Exception(f"Error creating study index: {e}") from e
        finally:
            self.client.close()
            log("Database connection closed.")
    
    def create_schema(self):
        """Create schema"""
        try:
            log("Creating schema.")
            self.create_study_table()
            self.create_study_index()
            log("Schema created successfully.")
        except Exception as e:
            raise Exception(f"Error creating schema: {e}") from e
        finally:
            self.client.close()
            log("Database connection closed.")
    
    def drop_schema(self):
        """Drop schema"""
        try:
            log("Dropping schema.")
            operation = self.database.update_ddl(["DROP INDEX StudyByModel", "DROP TABLE Study"])
            operation.result(config.SPANNER_TIMEOUT)
            log("Schema dropped successfully.")
        except Exception as e:
            raise Exception(f"Error dropping schema: {e}") from e
        finally:
            self.client.close()
            log("Database connection closed.")

if __name__ == "__main__":
    # Create an instance of the ArenaStudySchema class
    schema = ArenaStudySchema(
        project_id=config.PROJECT_ID,
        spanner_instance_id=config.SPANNER_INSTANCE_ID,
        spanner_database_id=config.SPANNER_DATABASE_ID
    )
    
    # TODO: DEPLOYMENT - Uncomment the following line to create the schema and tables
    # schema.create_schema()
    # schema.drop_schema()