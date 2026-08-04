import os
import asyncio
import time
import mimetypes
import io
from PIL import Image as PILImage
from pathlib import Path
from google import genai
from google.genai import types
from google.cloud import storage

def load_image_for_veo(image_path):
    """Loads an image file, ensuring proper JPEG/PNG mime type and format for Veo."""
    try:
        with PILImage.open(image_path) as img:
            fmt = (img.format or "").upper()
            if fmt == "PNG":
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue(), "image/png"
            else:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                return buffer.getvalue(), "image/jpeg"
    except Exception as e:
        print(f"PIL loading failed for {image_path}: {e}, falling back to raw bytes")
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type not in ["image/jpeg", "image/png"]:
            mime_type = "image/jpeg"
        with open(image_path, "rb") as f:
            return f.read(), mime_type

def get_veo_client(project_id, location):
    if not project_id:
        raise ValueError("Project ID must be provided.")
    
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        http_options=types.HttpOptions(
            api_version='v1beta1'
        )
    )

def download_from_gcs(gcs_uri, local_path):
    """Downloads a file from GCS using the Python Storage SDK."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    
    parts = gcs_uri[5:].split("/", 1)
    bucket_name = parts[0]
    blob_name = parts[1]
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)
    return local_path

async def generate_video(prompt, model, duration, project_id, location, bucket, output_dir, 
                         image_path=None, aspect_ratio="16:9"):
    """
    Generates a video natively using the google-genai Python SDK.
    """
    model_id = model.split('/')[-1]
    client = get_veo_client(project_id, location)
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    gcs_bucket_name = bucket.replace("gs://", "").rstrip("/")
    gcs_prefix = f"var_{timestamp}_{model_id.replace('.', '_')}"
    gcs_output_path = f"gs://{gcs_bucket_name}/{gcs_prefix}/"

    image = None
    if image_path:
        img_bytes, mime_type = load_image_for_veo(image_path)
        image = types.Image(image_bytes=img_bytes, mime_type=mime_type)

    try:
        operation = client.models.generate_videos(
            model=model_id,
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(
                duration_seconds=duration,
                aspect_ratio=aspect_ratio,
                output_gcs_uri=gcs_output_path
            )
        )
        
        while not operation.done:
            await asyncio.sleep(10)
            operation = client.operations.get(operation)
            
        if operation.error:
            raise Exception(f"Generation failed for {model_id}: {operation.error}")
            
        if not operation.result or not operation.result.generated_videos:
            raise Exception(f"No videos found in operation result for {model_id}")
            
        video_uri = operation.result.generated_videos[0].video.uri
        local_filename = f"veo-{model_id}-{timestamp}.mp4"
        local_path = os.path.join(output_dir, local_filename)
        
        download_from_gcs(video_uri, local_path)
        
        return local_filename

    except Exception as e:
        raise e
