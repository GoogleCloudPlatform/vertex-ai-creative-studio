"""
Load and process the Metadata file of the DiffusionDB dataset.
This script is adapted from DiffusionDB github repo: https://github.com/poloclub/diffusiondb?tab=readme-ov-file
"""

import json
import pandas as pd
from urllib.request import urlretrieve
import os
from collections import defaultdict

SAFETY_RATIO = 0.03
METADATA_URL = 'https://huggingface.co/datasets/poloclub/diffusiondb/resolve/main/metadata.parquet'
METADATA_FILE = 'metadata.parquet'
FILTERED_METADATA_FILE = 'diffusiondb_metadata.json'
PROMPTS_IDS_FILE = 'prompt_image_names.json'


def download_metadata(url: str, filename: str) -> None:
    """Downloads the metadata file from the given URL."""
    print("Downloading the metadata table...")
    urlretrieve(url, filename)
    print("Download complete!")


def load_metadata(filename: str) -> pd.DataFrame:
    """Loads the metadata table into a Pandas DataFrame."""
    print("Loading the metadata table...")
    return pd.read_parquet(filename)


def filter_metadata(df: pd.DataFrame, safety_ratio: float) -> pd.DataFrame:
    """Filters the metadata DataFrame based on NSFW ratios."""
    filtered_df = df[
        (df['image_nsfw'] < safety_ratio) & (df['prompt_nsfw'] < safety_ratio)
    ]
    print("Filtering complete!")
    print(f"Total number of images: {len(df)}")
    print(f"Number of images after filtering: {len(filtered_df)}")
    return filtered_df


def map_unique_prompts_to_image_ids(df: pd.DataFrame) -> list:
    """
    Creates a list of tuples (prompt, [image_ids]) from unique prompts.

    Args:
        df: The Pandas DataFrame containing the data.

    Returns:
        A list of tuples, where each tuple contains a unique prompt and a list of image_ids.
    """
    prompt_to_image_ids = defaultdict(list)

    for prompt, image_id in zip(df['prompt'], df['image_name']):
        prompt_to_image_ids[prompt].append(image_id)

    print(f"Number of unique prompts: {len(prompt_to_image_ids)}")
    return list(prompt_to_image_ids.items()) 


def save_prompt_ids_to_json(prompt_ids_list: list, filename: str) -> None:
    """Saves the list of tuples (prompt, [image_name]) to a JSON file."""
    print("Saving unique prompts to image_name...")
    data = {"stable_diffusion": prompt_ids_list}
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def save_filtered_metadata(df: pd.DataFrame, filename: str) -> None:
    """Saves the filtered DataFrame to a JSON file."""
    print("Saving the filtered metadata table...")
    df.to_json(filename, orient='records', indent=4)


def main():
    """Main function to orchestrate the metadata processing."""

    if not os.path.exists(METADATA_FILE):
        download_metadata(METADATA_URL, METADATA_FILE)

    metadata_df = load_metadata(METADATA_FILE)
    filtered_df = filter_metadata(metadata_df, SAFETY_RATIO)
    prompt_image_id_list = map_unique_prompts_to_image_ids(filtered_df)

    save_prompt_ids_to_json(prompt_image_id_list, PROMPTS_IDS_FILE)
    save_filtered_metadata(filtered_df, FILTERED_METADATA_FILE)
    # Clean up the downloaded metadata file
    os.remove(METADATA_FILE)

if __name__ == "__main__":
    main()