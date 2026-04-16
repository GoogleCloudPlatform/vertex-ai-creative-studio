# Promptlandia Project Guide

This guide provides essential, actionable information for working with the Promptlandia application.

## Project Structure Overview

- **`app.py`**: Main application entry point.
- **`components/`**: Reusable UI components built with the Mesop framework.
- **`models/`**: Handles all interaction with the Google Generative AI SDK.
  - **`gemini.py`**: Contains the core logic for making API calls to the Gemini model. This is the primary file to modify for GenAI interactions.
  - **`prompts.py`**: Stores the static prompts used for prompt evaluation and improvement.
- **`pages/`**: Defines the different pages (views) of the web application.
- **`state/`**: Manages the application's reactive state.
- **`tests/`**: Contains end-to-end tests using Playwright and pytest.
- **`developers_guide.md`**: Provides a more detailed, human-oriented guide with sections on future improvements.

## Development Workflow

### Running the Application

The application is built with the [Mesop](https://google.github.io/mesop/) framework. To run it locally:

1.  **Set up the environment:** Create a `.env` file from the `.env.dotenv` template and populate it with your GCP project details.

    If the .env exists, do not overwrite it.

    If .env does not exist, this is how you create a default one:

    ```bash
    cp .env.dotenv .env
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```
3.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```
4.  **Start the development server:**
    ```bash
    mesop app.py
    ```

### Testing

The project uses `pytest` and `playwright` for end-to-end testing.

**To run the tests:**

1.  Ensure the Mesop application is running in a separate terminal (`mesop app.py`).
2.  Execute `pytest` in another terminal:
    ```bash
    pytest
    ```

## Deployment

This application is deployed using Google Cloud Run.

### Initial Setup (One-time)

Create a service account and grant it the necessary permissions.

```bash
export PROJECT_ID=$(gcloud info --format='value(config.project)')
export SA_NAME="sa-promptlandia"
export SA_ID=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

# Create service account
gcloud iam service-accounts create $SA_NAME --description "promptlandia" --display-name $SA_NAME

# Assign necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SA_ID}" --role "roles/aiplatform.user"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SA_ID}" --role "roles/run.invoker"
```

### Deployment Commands

Set these environment variables before deploying:
```bash
export PROJECT_ID=$(gcloud info --format='value(config.project)')
export SA_ID=sa-promptlandia@${PROJECT_ID}.iam.gserviceaccount.com
```

**To deploy an unauthenticated service:**
```bash
gcloud run deploy promptlandia --source . --service-account=$SA_ID --region us-central1 --set-env-vars PROJECT_ID=$(gcloud config get project),MODEL_ID=gemini-3.1-pro-preview,LOCATION=us-central1 --allow-unauthenticated
```

**To deploy a service secured with IAP:**
```bash
gcloud alpha run deploy promptlandia --source . --iap --service-account=$SA_ID --region us-central1 --set-env-vars PROJECT_ID=$(gcloud config get project),MODEL_ID=gemini-3.1-pro-preview,LOCATION=us-central1
```


## Committing

When committing changes, please use the `.commit.txt` file to generate a commit message.