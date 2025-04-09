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
"""Script to load SD metadata into Firestore."""
import json
from typing import Optional
import fire
from config.default import Default
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

cfg = Default()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main(
        collection_name: str = None,
        json_file_path: str = None,
        top_level_key: Optional[str] = "stable_diffusion",
        gcs_sub_folder: Optional[str] = "stablediffusion",
        model_name: Optional[str] = cfg.MODEL_STABLE_DIFFUSION,
        prompt_image_mapping: Optional[dict[int, str]] = {0: "prompt", 1: "images"}
):
    """
    Loads metadata from a JSON file and stores it in a Firestore collection.

    This function reads a JSON file containing image metadata, typically prompts
    and associated image filenames, and iterates through its entries to upload
    the prompt and construct the Google Cloud Storage (GCS) URI for one of the
    associated images. It then uses the `load_metadata_from_json` function
    (assumed to be imported from `common.metadata`) to process this information
    and store it as a document in the specified Firestore collection.

    The function is designed to be run from the command line using the `fire`
    library, allowing users to override default configuration values through
    command-line arguments.

    Args:
        firestore_collection_name (str, optional): The name of the Firestore
            collection where the metadata will be stored. Defaults to the value
            of `Default.IMAGE_COLLECTION_NAME` from the `config.default` module.
        json_file_path (str, optional): The path to the JSON file containing the
            metadata. Defaults to the value of
            `Default.STABLE_DIFFUSION_DB_PROMPTS` from the `config.default`
            module. This file is expected to have a top-level key (specified by
            `top_level_key`) whose value is a list of entries. Each entry is
            expected to map a prompt to a list of associated image filenames
            according to the `prompt_image_mapping`.
        top_level_key (str, optional): The top-level key in the JSON file that
            contains the list of metadata entries to process. Defaults to
            "stable_diffusion".
        gcs_sub_folder (str, optional): The sub-folder within the Google Cloud
            Storage bucket where the image files are located. This is used to
            construct the full GCS URI for an image. Defaults to "stablediffusion".
        model_name (str, optional): The name of the machine learning model
            associated with the generated images. This will be stored as part
            of the metadata in Firestore. Defaults to the value of
            `Default.MODEL_STABLE_DIFFUSION` from the `config.default` module.
        prompt_image_mapping (dict[int, str], optional): A dictionary that
            specifies how to extract the prompt and list of image filenames from
            each entry in the list found under the `top_level_key` in the JSON
            file. The keys of this dictionary are expected to be integer indices
            (representing the position in a list or tuple), and the values are
            strings representing the semantic meaning of the element at that
            index (e.g., "prompt" and "images"). Defaults to `{0: "prompt", 1: "images"}`,
            indicating that each entry is a list or tuple where the first element
            is the prompt and the second element is a list of image filenames.

    Raises:
        FileNotFoundError: If the specified `json_file_path` does not exist.
        json.JSONDecodeError: If the content of the `json_file_path` cannot be
            parsed as valid JSON.
        ValueError: If the `top_level_key` is not found in the loaded JSON,
            or if the structure of the data under that key does not conform
            to the expectations defined by `prompt_image_mapping`.
        Other exceptions: May be raised by the underlying
            `load_metadata_from_json` function or GCS/Firestore client
            operations.

    Example Usage (from the command line):
        ```
        python load_metadata_to_firestore.py --json_file_path path/to/metadata.json --firestore_collection_name my_images
        ```

        ```
        python load_metadata_to_firestore.py --top_level_key generated_art --gcs_sub_folder final_renders
        ```

        ```
        python load_metadata_to_firestore.py --prompt_image_mapping "{'text': 'prompt', 'files': 'images'}"
        ```
    """
    try:
        from common.metadata import load_metadata_from_json # lazy import 
        load_metadata_from_json(
            collection_name=collection_name,
            json_file_path=json_file_path,
            top_level_key=top_level_key,
            gcs_sub_folder=gcs_sub_folder,
            model_name=model_name,
            key_mapping=prompt_image_mapping
        )
        logging.info("Metadata loading process completed successfully.")
    except FileNotFoundError as e:
        logging.error(f"Error: Metadata file not found at '{json_file_path}'. {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Error: Failed to decode JSON from '{json_file_path}'. {e}")
    except ValueError as e:
        logging.error(f"Error during metadata loading: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fire.Fire(main)