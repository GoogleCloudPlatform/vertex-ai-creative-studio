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
#import numpy as np 
import pandas as pd

from components.header import header  
from components.page_scaffold import (  
    page_frame,
    page_scaffold,
)
from config.default import Default
from state.state import AppState  


@me.page(path="/config", title="GenMedia Creative Studio - Config")
def config_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold(page_name="config"):  # pylint: disable=not-context-manager
        config_page_contents(state)  


def get_config_table(app_state: AppState):
    """Construct a table of the Defaults, including optional new attributes"""

    # app_state = me.state(AppState) # Not currently used in this function

    # Start with a base list of configurations
    config_data = {
        "Config": [
            "Username",
            "Vertex AI Enabled",
            "Project ID",
            "Location",
            "Default Model ID",
            "GenMedia Bucket",
            "GenMedia Firestore DB / Collection",
            "Veo Project ID",
            "Veo Model ID",
            "Veo Experimental Model ID",
        ],
        "Value": [
            app_state.user_email if app_state.user_email else "Anonymous",
            str(Default.INIT_VERTEX),
            Default.PROJECT_ID,
            Default.LOCATION,
            Default.MODEL_ID,
            f"gs://{Default.GENMEDIA_BUCKET}" if Default.GENMEDIA_BUCKET else "Not Set",
            f"{Default.GENMEDIA_FIREBASE_DB} / {Default.GENMEDIA_COLLECTION_NAME}"
            if Default.GENMEDIA_FIREBASE_DB and Default.GENMEDIA_COLLECTION_NAME
            else "Not Set",
            Default.VEO_PROJECT_ID,
            Default.VEO_MODEL_ID,
            Default.VEO_EXP_MODEL_ID,
        ],
    }

    # Conditionally add new configurations if they exist and have a value
    # Example: LYRIA_PROJECT_ID
    if hasattr(Default, "LYRIA_PROJECT_ID"):
        lyria_project_id_val = getattr(Default, "LYRIA_PROJECT_ID")
        if (
            lyria_project_id_val is not None and lyria_project_id_val != ""
        ):  # Check if it has a meaningful value
            config_data["Config"].append("Lyria Project ID")
            config_data["Value"].append(lyria_project_id_val)
        config_data["Config"].append("Lyria Model Version")
        config_data["Value"].append(Default.LYRIA_MODEL_VERSION)

    df = pd.DataFrame(data=config_data)
    return df


def config_page_contents(app_state: me.state):  # pylint: disable=unused-argument
    """Configurations page content"""
    with page_frame():  # pylint: disable=not-context-manager
            header("Configurations", "settings")

            me.table(
                get_config_table(app_state),
                header=me.TableHeader(sticky=True),
                columns={
                    "Config": me.TableColumn(sticky=True),
                    "Value": me.TableColumn(sticky=True),
                },
            )
