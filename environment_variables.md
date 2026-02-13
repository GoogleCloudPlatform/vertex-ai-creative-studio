# Application Environment Variables Explainer

This document details the environment variables used in the application, as defined in `config/default.py`. These variables control infrastructure settings, model versions, storage locations, and feature configurations.

> **Quick Start:** A `dotenv.template` file is provided in the root directory. To set up your local environment, copy this file to `.env` and populate the values:
> ```bash
> cp dotenv.template .env
> ```

## 🌍 Core Infrastructure & Environment
These variables define the fundamental operating context of the application.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`PROJECT_ID`** | *None* (Required) | The Google Cloud Project ID where resources (Vertex AI, Firestore, Storage) are located. |
| **`LOCATION`** | `us-central1` | The default GCP region for most services (Vertex AI, etc.). |
| **`APP_ENV`** | `""` (Empty) | Defines the environment name (e.g., `dev`, `godemos`). This is used as a metadata tag on the Config page. |
| **`GMCS_OVERRIDE_PATH`** | *None* | **(Development Only)** An absolute path to a directory containing configuration overrides. If a file exists in this path (e.g., `config/about_content.json`), the app will prioritize it over the local version. |
| **`API_BASE_URL`** | `http://localhost:{PORT}` | The base URL for the application's backend APIs. |
| **`PORT`** | `8080` | The port the application server listens on. |
| **`SERVICE_ACCOUNT_EMAIL`** | *None* | The email of the service account used for authentication, if applicable. |
| **`GA_MEASUREMENT_ID`** | *None* | Google Analytics Measurement ID for tracking user interactions. |

## 🧠 Gemini Models (Text & Multimodal)
Controls which versions of the Gemini models are used for various tasks.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`MODEL_ID`** | `gemini-2.5-flash` | The primary Gemini model used for general text and reasoning tasks throughout the app. |
| **`GEMINI_IMAGE_GEN_MODEL`** | `gemini-2.5-flash-image` | The specific model used for image generation features. |
| **`GEMINI_IMAGE_GEN_LOCATION`** | `global` | The region for the Gemini Image Generation API. |
| **`GEMINI_AUDIO_ANALYSIS_MODEL_ID`** | `gemini-2.5-flash` | The model used specifically for analyzing audio content. |
| **`GEMINI_WRITERS_WORKSHOP_MODEL_ID`** | `MODEL_ID` | The model used for the Gemini Writers Workshop page. Defaults to `MODEL_ID`. |

## 🎥 Veo (Video Generation)
Configuration for the Veo video generation models.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`VEO_MODEL_ID`** | `veo-2.0-generate-001` | The standard Veo model version. |
| **`VEO_PROJECT_ID`** | `PROJECT_ID` | Allows using a different project for Veo quota if needed. |
| **`VEO_EXP_MODEL_ID`** | `veo-3.0-generate-001` | The experimental/newer Veo model version. |
| **`VEO_EXP_FAST_MODEL_ID`** | `veo-3.0-fast-generate-001` | The faster, lower-latency experimental Veo model. |
| **`VEO_EXP_PROJECT_ID`** | `PROJECT_ID` | Project ID for experimental Veo models. |

## 🎨 Imagen (Image Generation & Editing)
Settings for Imagen models, including specialized versions for editing and product shots.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`MODEL_IMAGEN_PRODUCT_RECONTEXT`** | `imagen-product-recontext-preview-06-30` | Model used for "Product Recontextualization" features. |
| **`IMAGEN_GENERATED_SUBFOLDER`** | `generated_images` | Subfolder in the GCS bucket where generated images are saved. |
| **`IMAGEN_EDITED_SUBFOLDER`** | `edited_images` | Subfolder for images resulting from editing operations. |

## 🛍️ Virtual Try-On (VTO)
Specific configuration for the Virtual Try-On feature.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`VTO_LOCATION`** | `us-central1` | Region for the VTO API. |
| **`VTO_MODEL_ID`** | `virtual-try-on-001` | The specific VTO model version. |
| **`GENMEDIA_VTO_MODEL_COLLECTION_NAME`** | `genmedia-vto-model` | Firestore collection for VTO model data. |
| **`GENMEDIA_VTO_CATALOG_COLLECTION_NAME`** | `genmedia-vto-catalog` | Firestore collection for VTO product catalog data. |

## 🎵 Lyria (Music Generation)
Configuration for the Lyria music generation model.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`LYRIA_LOCATION`** | `us-central1` | Region for Lyria API calls. |
| **`LYRIA_MODEL_VERSION`** | `lyria-002` | The version of the Lyria model to use. |
| **`LYRIA_PROJECT_ID`** | `PROJECT_ID` | Project ID for Lyria quota. |

## 💾 Storage & Database (Firebase/GCS)
Defines where data and media assets are stored.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`GENMEDIA_FIREBASE_DB`** | `(default)` | The Firestore database ID. |
| **`GENMEDIA_COLLECTION_NAME`** | `genmedia` | The main Firestore collection for storing generation metadata. |
| **`SESSIONS_COLLECTION_NAME`** | `sessions` | Firestore collection for user session data. |
| **`GENMEDIA_BUCKET`** | `{PROJECT_ID}-assets` | The primary GCS bucket for storing generated media. |
| **`VIDEO_BUCKET`** | `{PROJECT_ID}-assets/videos` | Specific bucket/path for video files. |
| **`IMAGE_BUCKET`** | `{PROJECT_ID}-assets/images` | Specific bucket/path for image files. |
| **`MEDIA_BUCKET`** | `{PROJECT_ID}-assets` | Used by Lyria and potentially other legacy components. |
| **`GCS_ASSETS_BUCKET`** | *None* | Bucket for static assets used in the "About" page. |

## ⚙️ Application Logic
| Variable | Default | Description |
| :--- | :--- | :--- |
| **`LIBRARY_MEDIA_PER_PAGE`** | `15` | Controls how many items appear per page in the media library. |
| **`USE_MEDIA_PROXY`** | `true` | If `true`, media URLs are proxied to avoid CORS/hotlinking issues. |

## 📦 Build Metadata
The application can display detailed build information on the **Config** page. This is populated from an optional JSON file:

*   **File Path**: `config/build.json` (or via `GMCS_OVERRIDE_PATH`)
*   **Format**:
    ```json
    {
      "commit": "a1b2c3d",
      "date": "2026-01-13 14:30:00"
    }
    ```
*   If present, these values populate the `BUILD_COMMIT` and `BUILD_DATE` fields in the application state.

## 🏗️ Terraform Configuration & Deployment

When deploying this application using Terraform (via `main.tf`), not all environment variables are exposed for configuration. The Terraform setup manages a specific subset of variables, primarily those related to infrastructure and core model IDs.

### 1. Variables Controllable via `variables.tf`
These variables are exposed in `variables.tf` and directly map to environment variables in the Cloud Run service. You can customize these by setting the corresponding Terraform variable during deployment.

| Terraform Variable | Maps to App Env Var | Default in Terraform |
| :--- | :--- | :--- |
| `project_id` | `PROJECT_ID` | *(Required)* |
| `region` | `LOCATION` | `us-central1` |
| `model_id` | `MODEL_ID` | `gemini-2.5-flash` |
| `veo_model_id` | `VEO_MODEL_ID` | `veo-3.0-generate-001` |
| `veo_exp_model_id` | `VEO_EXP_MODEL_ID` | `veo-3.0-generate-preview` |
| `lyria_model_id` | `LYRIA_MODEL_VERSION` | `lyria-002` |
| `edit_images_enabled` | `EDIT_IMAGES_ENABLED` | `true` |

### 2. Variables Automatically Managed by Terraform
These variables are computed within `main.tf` based on the resources Terraform creates (e.g., bucket names, service account emails). You generally **cannot** change these via `variables.tf` as they ensure the application correctly connects to the provisioned infrastructure.

| App Env Var | Source in `main.tf` | Value Logic |
| :--- | :--- | :--- |
| `GENMEDIA_BUCKET` | `local.asset_bucket_name` | `creative-studio-{project_id}-assets` |
| `VIDEO_BUCKET` | `local.asset_bucket_name` | Same as above |
| `MEDIA_BUCKET` | `local.asset_bucket_name` | Same as above |
| `IMAGE_BUCKET` | `local.asset_bucket_name` | Same as above |
| `GCS_ASSETS_BUCKET` | `local.asset_bucket_name` | Same as above |
| `GENMEDIA_FIREBASE_DB` | Resource Attribute | Name of the created Firestore DB |
| `SERVICE_ACCOUNT_EMAIL`| Resource Attribute | Email of the created Service Account |
| `LYRIA_PROJECT_ID` | `var.project_id` | Forces Lyria to use the main project ID |

### 3. Variables NOT Set by Terraform (Using Python Defaults)
The following variables are **not** explicitly set in the `main.tf` configuration. This means the application will use the **default values defined in `config/default.py`** when deployed via Terraform.

*   **Gemini Models:** `GEMINI_IMAGE_GEN_MODEL`, `GEMINI_IMAGE_GEN_LOCATION`, `GEMINI_AUDIO_ANALYSIS_MODEL_ID`
*   **Veo:** `VEO_PROJECT_ID`, `VEO_EXP_FAST_MODEL_ID`, `VEO_EXP_PROJECT_ID`
*   **VTO (Virtual Try-On):** `VTO_LOCATION`, `VTO_MODEL_ID`, `GENMEDIA_VTO_*` collection names.
*   **Imagen:** `MODEL_IMAGEN_PRODUCT_RECONTEXT`, `IMAGEN_GENERATED_SUBFOLDER`, `IMAGEN_EDITED_SUBFOLDER`
*   **App Logic:** `APP_ENV`, `API_BASE_URL`, `GA_MEASUREMENT_ID`, `LIBRARY_MEDIA_PER_PAGE`, `USE_MEDIA_PROXY`
*   **Collections:** `GENMEDIA_COLLECTION_NAME`, `SESSIONS_COLLECTION_NAME`

### 🛠️ How to Deploy with Custom Values
To change a variable from **Group 3** (e.g., `GEMINI_IMAGE_GEN_MODEL`) when deploying with Terraform:

1.  **Modify `variables.tf`:** Add a new variable definition.
    ```hcl
    variable "gemini_image_model" {
      description = "Model ID for Gemini Image Generation"
      type        = string
      default     = "gemini-3-pro-image-preview"
    }
    ```
2.  **Modify `main.tf`:** Update the `locals` block to include the new environment variable mapping.
    ```hcl
    locals {
      creative_studio_env_vars = {
        # ... existing vars ...
        GEMINI_IMAGE_GEN_MODEL = var.gemini_image_model
      }
    }
    ```
