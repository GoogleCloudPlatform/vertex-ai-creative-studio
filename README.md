# Creative Studio | Vertex AI

Creative Studio is an app that highlights the capabilities of Google Cloud Vertex AI generative AI creative APIs, including Imagen, the text-to-image model.

This app is built with [Mesop](https://google.github.io/mesop), an unofficial Google Python UX framework.


## Imagen | Creative Studio

![](./screenshots/creative_studio.png)



## Run locally

Provide an environment variable for your Google Cloud Project ID

```
export PROJECT_ID=$(gcloud config get project)
```

### Install requirements

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

```

Modify one item in `main.py`
* `image_creation_bucket` a GCS url of a bucket the app can write to, this is where images will be generated and retrieved from

Optionally, modify this
* (Optional) `template_portrait_base_url` point this to a public bucket of template images, see `templates` folder and the `templates.json`



### Run with mesop

```
mesop main.py
```


## Deploy to Cloud Run

```
gcloud run deploy creative-studio --source . --allow-unauthenticated --region us-central1
```

It's recommended that you create a separate service account to deploy a Cloud Run Service.

