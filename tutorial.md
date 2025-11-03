# GenMedia Creative Studio: Veo 2 module Tutorial

## Welcome!

If you're seeing this, you've cloned the correct repository, and you should be in the `experiments/veo-app` directory! Let's get started.

<walkthrough-project-setup></walkthrough-project-setup>


## First step: auth to your Google Cloud Project

Type this command in the shell, substituting your project name

```bash
gcloud config set project <walkthrough-project-name/>
export PROJECT_ID=$(gcloud config get project)
```


## Second steps: Project prerequisites

### Firestore

For the defaults, a Firestore database should be set up.

To check your Firestore databases (we're looking for a Standard database named "(default)"):

```bash
gcloud firestore databases list
```

If you don't have the default one, create one:

```bash
gcloud firestore databases create --database="(default)" --location=nam5
```

### Google Cloud Storage bucket

For the defaults, you should have a bucket named <walkthrough-project-name/>-assets, and you can check by doing this:

```bash
gcloud storage ls gs://<walkthrough-project-name/>-assets
```

If you have one, great! If not, create one:

```bash
gcloud storage buckets create -l us-central1 gs://<walkthrough-project-name/>-assets
```

Notre

### uv

[uv](https://github.com/astral-sh/uv) is a fast Python package manager. Since this app is written in Python, we'll use this to install prerequisites.

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Third step: Start the app

Use uv to sync the prerequisites, activate the Python virtual environment, and start the app!

```bash
uv sync
source .venv/bin/activate
uv run main.py
#mesop main.py
```

If you get an error that `/` is not found, navigate to `/home`

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>
