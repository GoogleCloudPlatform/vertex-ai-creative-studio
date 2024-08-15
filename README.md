# Creative Studio | Vertex AI

Creative Studio is an app that highlights the capabilities of Google Cloud Vertex AI generative AI creative APIs, including Imagen, the text-to-image model.

This app is built with [Mesop](https://google.github.io/mesop), an unofficial Google Python UX framework.


## GenMedia | Creative Studio

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

To run locally, use the `mesop` command and open the browser to the URL provided:

```
mesop main.py
```


## Deploy to Cloud Run

Deploy this application to a Cloud Run service.

It's recommended that you create a separate service account to deploy a Cloud Run Service.


```
export SA_NAME=sa-genmedia-creative-studio
export PROJECT_ID=$(gcloud config get project)

gcloud iam service-accounts create $SA_NAME \
    --description="genmedia creative studio" \
    --display-name="$SA_NAME"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectUser"
```

Deploy with the service account and environment variables (see above).

```
gcloud run deploy creative-studio --source . \
  --allow-unauthenticated --region us-central1 \
  --service-account $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
  --update-env-vars=GENMEDIA_BUCKET=$GENMEDIA_BUCKET,PROJECT_ID=$PROJECT_ID
```
