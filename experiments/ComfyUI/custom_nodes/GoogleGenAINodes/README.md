# ComfyUI Imagen Node (google-genai)

This directory contains a custom ComfyUI node for generating images using Google's Imagen models via the `google-genai` library for Vertex AI.

## Setup and Installation

1.  **Create Directory:**
    Ensure this node's code is placed in the correct ComfyUI directory structure. This typically means having this `GoogleGenAINodes` folder inside your `ComfyUI/custom_nodes/` directory. So the path would be `ComfyUI/custom_nodes/GoogleGenAINodes/`.

2.  **Install Prerequisites:**
    Install the necessary Python libraries. Open your terminal or command prompt and run:
    ```bash
    pip install google-genai Pillow numpy torch
    ```

3.  **Google Cloud Authentication:**
    Ensure your environment is authenticated to Google Cloud. The `google-genai` library, when used with `vertexai=True`, will attempt to find Application Default Credentials (ADC). You can set these up by running:
    ```bash
    gcloud auth application-default login
    ```
    Alternatively, if ComfyUI is running in an environment with a configured service account (e.g., a Google Cloud VM), ensure that service account has the necessary permissions for Vertex AI.

4.  **Enable Vertex AI API:**
    Make sure the Vertex AI API is enabled in your Google Cloud project. You can do this through the Google Cloud Console.

5.  **Project and Location:**
    You will need your Google Cloud Project ID and the desired location (region) for the node's configuration. You can set these as environment variables (`GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_REGION`) or enter them directly in the node's properties in ComfyUI.

## How to Use

1.  **Restart ComfyUI:** After ensuring the files are in the correct location and prerequisites are installed, restart your ComfyUI instance.
2.  **Find the Node:** In the ComfyUI interface, right-click to "Add Node". You should find the "Imagen Generator (google-genai)" node under the "GoogleGenAI/Imagen" category.
3.  **Configure Inputs:**
    *   **`project_id`**: Your Google Cloud Project ID.
    *   **`location`**: The Google Cloud region (e.g., `us-central1`).
    *   **`model_id`**: Select the Imagen model you wish to use from the dropdown.
    *   **`prompt`**: Enter your text prompt for image generation.
    *   **`number_of_images`**: Specify how many images to generate (typically 1-4, model dependent).
    *   **`aspect_ratio`**: Choose the desired aspect ratio for the output images.
    *   **`safety_filter_level`**: Select the content safety filtering level.
    *   **`person_generation`**: Configure how images of people are handled.
    *   **`seed` (optional)**: Set a seed for reproducible results. A value of -1 usually means random.
4.  **Generate:** Connect the inputs/outputs as needed in your workflow and queue the prompt. The generated images will be available as an output, along with a status message.
5.  **Check Console:** Monitor the ComfyUI console (the terminal window where you launched ComfyUI) for any informational messages or errors, especially during the first run.

## Important Considerations

*   **`google-genai` Library Version:** The behavior and configuration options (especially for `GenerateImagesConfig`) can change between versions of the `google-genai` library. Always refer to the official documentation for the version you have installed if you encounter issues or want to explore advanced configurations.
*   **Model Identifiers:** The list of `model_id`s in the node are examples. Ensure that the selected model ID is valid for use with `genai.Client(vertexai=True, ...)` and the `client.models.generate_images()` method. Some models might have specific availability or naming conventions.
*   **Error Handling:** The node includes basic error handling. For more complex issues (e.g., quota limits, authentication problems), you might need to consult the ComfyUI console logs and Google Cloud documentation.
*   **Seed and Negative Prompt:** The current version of the node includes `seed`. Support for features like `negative_prompt` depends on their availability in the `google-genai` library's `GenerateImagesConfig` for Vertex AI Imagen models. If such features are supported by the library, the node can be updated accordingly.
