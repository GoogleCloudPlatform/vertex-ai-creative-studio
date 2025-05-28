# In ComfyUI/custom_nodes/GoogleGenAINodes/__init__.py

from .imagen_node import ImagenNode, GOOGLE_GENAI_SDK_AVAILABLE # Corrected class and variable names

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if GOOGLE_GENAI_SDK_AVAILABLE: # Corrected variable name
    NODE_CLASS_MAPPINGS["ImagenNode"] = ImagenNode # Corrected class name
    NODE_DISPLAY_NAME_MAPPINGS["ImagenNode"] = "Imagen Generator (google-genai)" # Corrected class name
    print("Loaded ImagenNode (using google-genai)") # Corrected class name
else:
    print("Skipping ImagenNode due to missing google-genai library.") # Corrected class name

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
