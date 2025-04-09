# GCS Directory Uploader

This Python script uploads files from a local directory to a Google Cloud Storage (GCS) bucket, leveraging parallel processing for efficient bulk uploads.

## Prerequisites

1. **Python 3.10+**
2. **Google Cloud SDK (gcloud) or Service Account Credentials:**
    * Ensure you have authenticated with Google Cloud. You can do this by:
        * Installing and configuring the Google Cloud SDK (`gcloud`) and logging in.
        * Setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account key file.
3. **Python Libraries:**
    * A `requirements.txt` file is provided that lists all necessary dependencies. For optimal installation speed and dependency management, it's recommended to use `uv` or `poetry`. If these are not available, `pip` can be used.

        **Using uv (Recommended for speed):**

        1. **Install uv:** If you don't have `uv` installed, you can install it using `pipx` (recommended) or `pip`.

            ```bash
            # Using pipx (recommended):
            pipx install uv

            # Using pip:
            pip install uv
            ```

        2. **Install dependencies:** Navigate to the directory containing `requirements.txt` and run:

            ```bash
            uv pip install -r requirements.txt
            ```

        **Using Poetry (Recommended for dependency management):**

        1. **Install Poetry:** If you don't have Poetry installed, follow the instructions on the [official Poetry website](https://python-poetry.org/docs/#installation).

        2. **Navigate to project directory:** Ensure you are in the directory containing `pyproject.toml` or `poetry.lock`.

        3. **Install dependencies:** Run:

            ```bash
            poetry install
            ```

            (Poetry will automatically create a virtual environment and install the dependencies listed in `pyproject.toml` or `poetry.lock`.)

        **Using pip (If uv or poetry are not available):**

        1. **Create a virtual environment (recommended):** It's best practice to create a virtual environment to isolate your project's dependencies.

            ```bash
            python -m venv venv
            # On Windows:
            venv\Scripts\activate
            # On macOS and Linux:
            source venv/bin/activate
            ```

        2. **Install dependencies:** Navigate to the directory containing `requirements.txt` and run:

            ```bash
            pip install -r requirements.txt
            ```

        This will install the `google-cloud-storage`, `python-fire`, and `alive-progress` libraries required to run the script.

## Usage

1. **Save the Script:** Save the provided Python script as a `.py` file (e.g., `gcs_bulk_uploader.py`).

2. **Run the Script:** Execute the script from your terminal, providing the necessary command-line arguments:

    ```bash
    python -m gcs_bulk_uploader --bucket_name YOUR_BUCKET_NAME --source_directory /path/to/local/directory [OPTIONS]
    ```

    * **IMPORTANT:** `YOUR_BUCKET_NAME` with the name of your GCS bucket. DO NOT INCLUDE THE `gs://` PREFIX.
    * **IMPORTANT:** `/path/to/local/directory` with the path to the directory you want to upload.

    For example:  

    ```bash
    python -m gcs_bulk_uploader --bucket_name arena_images_gcs_bucket --source_directory /home/user/my_images
    ```

3. **Command-Line Options:**

    * `--bucket_name`: (Required) The name of the GCS bucket. Without the `gs://` prefix.
    * `--source_directory`: (Required) The path to the local directory containing the files.
    * `--destination_prefix`: (Optional) A prefix for the GCS object names (e.g., `images/`). Defaults to an empty string (no prefix).
    * `--verbose`: (Optional) Enable verbose output, including upload progress and logging. Use `--verbose` or omit it.
    * `--skip_if_exists`: (Optional) Skip uploading files that already exist in the GCS bucket. Use `--skip_if_exists` or omit it.
    * `--extensions`: (Optional) A comma-separated list of file extensions to include (e.g., `png,json`). If omitted, all files will be uploaded.
    * `--project_id`: (Optional) The Google Cloud Project ID that contains the GCS bucket. If omitted, the default project from your environment's credentials will be used.

    **Example:**

    ```bash
    python -m gcs_bulk_uploader --bucket_name arena_images_gcs_bucket --source_directory /home/user/my_images --destination_prefix images/ --verbose --extensions png,jpg --project_id my-gcp-project
    ```

4. **Help:**

    * To see the available options, use the `--help` flag:

        ```bash
        python -m gcs_bulk_uploader --help
        ```

## Script Details

* **Parallel Uploads:** The script uses `google.cloud.storage.transfer_manager` for efficient parallel uploads, significantly speeding up the transfer process.
* **Logging:** The script uses the `logging` module to provide detailed log messages.
* **Progress Bar:** The `alive_progress` library is used to display a live progress bar during the upload.
* **File Extension Filtering:** The `--extensions` option allows you to upload only files with specific extensions.
* **Singleton Pattern:** The `GCSUploader` class uses the singleton pattern to ensure that only one instance is created per bucket and project, optimizing resource usage.
* **CLI Parameter Management:** The `fire` library is used to manage command-line arguments, making it easy to use the script from the terminal.
* **Project ID specification:** the `--project_id` option allows the user to specify the project in which the bucket resides.

## Error Handling

* The script includes robust error handling to catch potential issues, such as invalid directory paths, network errors, and GCS upload failures.
* Error messages are logged to the console, and in some cases, the user is prompted to check the logs for more information.

## Notes

* Ensure that you have the necessary permissions to access the specified GCS bucket.
* For large directories, the upload process may take some time.
* The number of worker processes is automatically set to the number of CPU cores on your machine.
* The script will overwrite existing files in the GCS bucket unless the `--skip_if_exists` option is used.
