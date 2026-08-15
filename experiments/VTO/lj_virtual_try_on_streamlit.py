# %%writefile vto.py
import streamlit as st
from PIL import Image
import base64
import io
import time
import os
import concurrent.futures
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic import PredictionServiceClient

# Must be first command
st.set_page_config(page_title="Virtual Try-On", layout="wide")

# Constants
PROJECT_ID = "consumer-genai-experiments"
LOCATION = "us-central1"
MODEL_ID = "virtual-try-on-001"
IMAGE_DIR = "/Users/layolin/Documents/VTO/tryon"
PRODUCT_IMAGE_FILES = ["red.jpg", "green.png", "dress.png", "blue.png", "yellow.png"]
TARGET_SIZE = (250, 550)
model_endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}"

# --- Utility functions with caching ---

@st.cache_data(show_spinner=False)
def load_image_bytes(path):
    with open(path, "rb") as f:
        return f.read()

@st.cache_data(show_spinner=False)
def encode_image(img_bytes):
    return base64.b64encode(img_bytes).decode("utf-8")

def prediction_to_pil_image(prediction, size=TARGET_SIZE):
    encoded = prediction["bytesBase64Encoded"]
    decoded = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(decoded)).convert("RGB")
    return image.resize(size)

# Optional: In-memory cache for try-on results
tryon_cache = {}

def run_tryon_cached(person_b64, name, b64):
    cache_key = (name, person_b64, b64)
    if cache_key in tryon_cache:
        return tryon_cache[cache_key]

    start = time.time()
    client = PredictionServiceClient(client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"})
    instances = [{
        "personImage": {"image": {"bytesBase64Encoded": person_b64}},
        "productImages": [{"image": {"bytesBase64Encoded": b64}}],
    }]
    response = client.predict(endpoint=model_endpoint, instances=instances, parameters={})
    elapsed = time.time() - start
    output_img = prediction_to_pil_image(response.predictions[0])
    tryon_cache[cache_key] = (output_img, elapsed)
    return output_img, elapsed

# --- Streamlit UI ---

st.title("👗 Virtual Try-On")
st.markdown("Upload your photo and click on dress images to try them on!")

uploaded_person = st.file_uploader("👤 Upload your photo", type=["jpg", "jpeg", "png"])

if uploaded_person:
    person_bytes = uploaded_person.read()
    person_img = Image.open(io.BytesIO(person_bytes)).convert("RGB").resize(TARGET_SIZE)
    person_b64 = encode_image(person_bytes)

    st.image(person_img, caption="👤 Your Uploaded Image")

    st.markdown("### 👗 Select Dresses (Click to Select)")

    if "selected_dresses" not in st.session_state:
        st.session_state.selected_dresses = set()

    cols = st.columns(len(PRODUCT_IMAGE_FILES))
    for i, file_name in enumerate(PRODUCT_IMAGE_FILES):
        img_path = os.path.join(IMAGE_DIR, file_name)
        product_bytes = load_image_bytes(img_path)
        img = Image.open(io.BytesIO(product_bytes)).convert("RGB").resize((100, 200))
        is_selected = file_name in st.session_state.selected_dresses

        with cols[i]:
            if st.button(f"{'✅' if is_selected else '🔲'} {file_name}", key=file_name):
                if is_selected:
                    st.session_state.selected_dresses.remove(file_name)
                else:
                    st.session_state.selected_dresses.add(file_name)
            st.image(img, caption="", use_container_width=True)

    if st.session_state.selected_dresses:
        if st.button("🚀 Generate Try-Ons"):
            st.markdown("### 👗 Try-On Results")
            product_data = []

            for file_name in st.session_state.selected_dresses:
                img_path = os.path.join(IMAGE_DIR, file_name)
                product_bytes = load_image_bytes(img_path)
                product_b64 = encode_image(product_bytes)
                product_data.append((file_name, product_b64))

            results = []

            with st.spinner("Generating results in parallel..."):
                def run_thread(item):
                    name, b64 = item
                    out_img, elapsed = run_tryon_cached(person_b64, name, b64)
                    return (name, out_img, elapsed)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = [executor.submit(run_thread, pd) for pd in product_data]
                    for f in concurrent.futures.as_completed(futures):
                        results.append(f.result())

            ordered_results = sorted(results, key=lambda x: PRODUCT_IMAGE_FILES.index(x[0]))
            cols = st.columns(len(ordered_results))
            for i, (name, out_img, elapsed) in enumerate(ordered_results):
                cols[i].image(out_img, caption=f"Time taken: {elapsed:.2f}s", use_container_width=True)
