import os
import io
import torch
import numpy as np
from PIL import Image

# Attempt to import Google Genai library
try:
    from google import genai # Corrected library name
    # The 'types' submodule is often used for config objects with genai
    from google.genai import types as genai_types # Corrected library name
    GOOGLE_GENAI_SDK_AVAILABLE = True # Corrected variable name
except ImportError:
    GOOGLE_GENAI_SDK_AVAILABLE = False # Corrected variable name
    print("Warning: google-genai library not found. ImagenNode will not be available.")
    # Define genai_types to None if import fails to prevent runtime errors in INPUT_TYPES
    genai_types = None


class ImagenNode: # Corrected class name
    CATEGORY = "GoogleGenAI/Imagen"

    @classmethod
    def INPUT_TYPES(s):
        if not GOOGLE_GENAI_SDK_AVAILABLE: # Corrected variable name
            return {"required": {"error": ("STRING", {"default": "Missing google-genai. Please install."})}}
        
        imagen_model_ids = [
            "imagegeneration@006", # Publisher model
            "imagen-3.0-generate-002", # Tuned model example
            "imagen-3.0-fast-generate-001", # Tuned model example
            "imagen-4.0-generate-preview-05-20", # Preview model
            "imagen-4.0-ultra-generate-exp-05-20", # Experimental model
            # Add other model IDs as needed, ensure they are accessible via genai.Client with vertexai=True
        ]
        
        # Safety filter levels and person generation options based on google.genai.types.GenerateImagesConfig
        # These might differ slightly from the aiplatform SDK's direct enum names/values.
        # Consult the google-genai documentation for exact valid string values if needed.
        safety_filter_levels = ["BLOCK_MEDIUM_AND_ABOVE", "BLOCK_LOW_AND_ABOVE", "BLOCK_ONLY_HIGH", "BLOCK_NONE"]
        person_generation_options = ["ALLOW_ADULT", "ALLOW_ALL", "DENY_ADULT"] # Example values from user snippet

        return {
            "required": {
                "project_id": ("STRING", {"default": os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")}),
                "location": ("STRING", {"default": os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")}),
                "model_id": (imagen_model_ids, {"default": "imagegeneration@006"}),
                "prompt": ("STRING", {"multiline": True, "default": "A charming illustration of a cat astronaut floating in space."}),
                "number_of_images": ("INT", {"default": 1, "min": 1, "max": 4}), # Max may vary by model
                "aspect_ratio": (["16:9", "1:1", "9:16", "4:3", "3:4"], {"default": "1:1"}),
                "safety_filter_level": (safety_filter_levels, {"default": "BLOCK_MEDIUM_AND_ABOVE"}),
                "person_generation": (person_generation_options, {"default": "ALLOW_ADULT"}),
            },
            "optional": {
                 "seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}), # Often, negative means random, 0 might be specific, or positive for specific seed.
                                                                                      # The genai library might have a specific way to handle this in GenerateImagesConfig.
                # "negative_prompt": ("STRING", {"multiline": True, "default": ""}), # If supported by GenerateImagesConfig
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING",)
    RETURN_NAMES = ("generated_images", "status_text",)
    FUNCTION = "generate_with_imagen" # Corrected function name to match class intent

    def generate_with_imagen(self, project_id, location, model_id, prompt, # Corrected function name
                                  number_of_images, aspect_ratio, 
                                  safety_filter_level, person_generation, seed=None):
        if not GOOGLE_GENAI_SDK_AVAILABLE or genai_types is None: # Corrected variable name and check genai_types as well
            return (None, "Error: google-genai library or its types submodule is not installed/loaded.")

        if not project_id or not location:
            return (None, "Error: Google Cloud Project ID and Location are required.")

        try:
            # Initialize the google.genai Client for Vertex AI
            client = genai.Client(vertexai=True, project=project_id, location=location)
        except Exception as e:
            return (None, f"Error initializing google.genai Client: {str(e)}")
        
        # Prepare the configuration for the API call
        # Note: The exact field names and accepted values for GenerateImagesConfig
        # should be confirmed with the google-genai library documentation
        # as they might differ from the aiplatform SDK or user's initial snippet.
        config_params = {
            "number_of_images": number_of_images,
            "aspect_ratio": aspect_ratio,
            "safety_filter_level": safety_filter_level,
            "person_generation": person_generation,
        }
        
        # Add seed if provided and non-negative (assuming genai API handles it this way)
        # The user's example GenerateImagesConfig didn't show seed.
        # If the API supports it in the config, add it here.
        if seed is not None and seed >= 0:
             if hasattr(genai_types.GenerateImagesConfig, 'seed'): # Check if 'seed' is a valid field
                config_params["seed"] = seed
             else:
                print(f"Warning: Seed parameter provided but 'seed' may not be a recognized field in genai_types.GenerateImagesConfig for model {model_id}. Ignoring seed.")


        try:
            # Create the config object
            image_gen_config = genai_types.GenerateImagesConfig(**config_params)

            # Make the API call
            # The model_id here refers to the publisher model endpoint or a tuned model name
            # accessible via this client setup.
            response = client.models.generate_images(
                model=model_id, # This should be the model identifier like "imagegeneration@006" or a tuned model path
                prompt=prompt,
                config=image_gen_config
            )

        except Exception as e:
            error_message = f"Error calling Imagen API with google-genai (model: {model_id}): {str(e)}"
            # Add more specific error checks if possible (e.g., for auth, quota)
            return (None, error_message)

        if not response or not hasattr(response, 'generated_images') or not response.generated_images:
            return (None, f"No images returned from API (model: {model_id}) or unexpected response structure.")

        output_images_np = []
        try:
            for generated_image_data in response.generated_images:
                # The user's example showed: `response_image = image.generated_images[0].image`
                # We assume `generated_image_data.image` contains the image data.
                # This could be raw bytes or already a PIL.Image object depending on the SDK version.
                # Let's try to handle both.
                
                img_bytes_or_pil = generated_image_data.image
                pil_image = None

                if isinstance(img_bytes_or_pil, Image.Image):
                    pil_image = img_bytes_or_pil
                elif isinstance(img_bytes_or_pil, bytes):
                    pil_image = Image.open(io.BytesIO(img_bytes_or_pil))
                else:
                    print(f"Warning: Unknown image data type in response from model {model_id}: {type(img_bytes_or_pil)}. Skipping this image.")
                    continue
                
                pil_image = pil_image.convert("RGB") # Ensure 3 channels
                np_image = np.array(pil_image).astype(np.float32) / 255.0 # H, W, C
                output_images_np.append(np_image)
        except Exception as e:
            return (None, f"Error processing image data from API response (model: {model_id}): {str(e)}")

        if not output_images_np:
            return (None, f"Failed to decode any images from API response (model: {model_id}).")

        # Stack into a batch tensor (B, H, W, C)
        batch_tensor = torch.from_numpy(np.stack(output_images_np))
        return (batch_tensor, f"{len(output_images_np)} image(s) generated successfully with {model_id}.")
