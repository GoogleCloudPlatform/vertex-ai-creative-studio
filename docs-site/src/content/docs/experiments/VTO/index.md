---
title: "Virtual Try-On with Generative AI"
---

**Author:** Layolin Jesudhass  
**Role:** Gen AI Solution Architect  

## Overview

This notebook demonstrates the use of a generative AI model for **Virtual Try-On**, allowing users to visualize various outfits on a given person image.

The solution leverages **Google Cloud Vertex AI Prediction API** and a pre-trained model to simulate how different outfits would appear when virtually worn. It includes both the code for inference and visual display of results in a Jupyter notebook.

## Features

- Upload and preprocess a person image.
- Load and encode multiple product images.
- Make predictions using a hosted Google Vertex AI model.
- Display all try-on results in a side-by-side comparison layout.
- Time and display each try-on result using concurrent processing for faster inference.

## Example Inputs

- **Person Image**: `model.png`
- **Outfits**:
  - `red.jpg`
  - `green.png`
  - `dress.png`
  - `blue.png`
  - `yellow.png`

## Technologies Used

- Python
- Jupyter Notebook
- PIL (Python Imaging Library)
- Google Cloud Vertex AI
- Base64 encoding
- `concurrent.futures` for parallel inference

## Setup Instructions

1. **Install required packages**:
    ```bash
    pip install google-cloud-aiplatform pillow
    ```

2. **Authenticate with Google Cloud**:
    Ensure your environment is authenticated with Google Cloud and has access to the specified project and model.

3. **Place required images**:
    Put your input images in the notebook's working directory:
    - `model.png` (person image)
    - Product images listed above

4. **Run the Notebook**:
    Execute the notebook cells step-by-step to:
    - Load and encode images
    - Run virtual try-on predictions
    - View results in-line

## Notes

- **Model Endpoint**:  
  The model is hosted on Google Cloud:

# Scaling
What works for small-scale
- Concurrent execution with ThreadPoolExecutor speeds up inference.
- Output is visually clear for up to ~10 products.
- Simple and understandable for demos or prototypes.

# Suggestions to scale this solution

✅ Backend/API scaling
Move image preprocessing and prediction to a backend service (e.g., Flask/FastAPI on Cloud Run).
Use asynchronous batching for predictions if supported by model endpoint.

✅ Efficient frontend
Store results in GCS or Firebase Storage.
Use a lightweight frontend (e.g., React or Streamlit) with paginated or scrollable UI.

✅ Parallelization
Use asyncio with aiohttp or multiprocessing for true parallelism beyond threading limits.
If using GCP Batch or Dataflow, process images in distributed jobs.


