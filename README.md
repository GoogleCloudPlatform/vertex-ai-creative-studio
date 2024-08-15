# Creative Studio | Vertex AI

Creative Studio is an app that highlights the capabilities of Google Cloud Vertex AI generative AI creative APIs, including Imagen, the text-to-image model.

Features Gemini for prompt rewriting as well as for a critic to provide a multimodal evaluation of the generated images. 

This app is built with [Mesop](https://google.github.io/mesop), a Python-based UI framework that allows you to rapidly build web apps like this demo and internal apps.


## GenMedia | Creative Studio

![](./screenshots/creative_studio_02.png)



## Run locally

Two environment variables are required to run this application:

`PROJECT_ID` 
Provide an environment variable for your Google Cloud Project ID

```
export PROJECT_ID=$(gcloud config get project)
```

`GENMEDIA_BUCKET`
Provide a Google Cloud Storage bucket for the generative media, without the gs:// url prefix, for example:

```
export GENMEDIA_BUCKET=myproject-genmedia/temp/
```

### Install requirements

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

```


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

Deploy with the service account and environment variables, `PROJECT_ID` and `GENMEDIA_BUCKET` (see above).

```
gcloud run deploy creative-studio --source . \
  --allow-unauthenticated --region us-central1 \
  --service-account $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
  --update-env-vars=GENMEDIA_BUCKET=$GENMEDIA_BUCKET,PROJECT_ID=$PROJECT_ID
```
