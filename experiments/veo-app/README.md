# Genmedia Creative Studio: v.Next

This is the next gen version of GenMedia Creative Studio

![Next Gen Experimental App UI](./assets/veo-app.png)


Current featureset
* Text to Video: Create a video from a prompt.
* Image to Video: Create a video from an image + prompt.
* Library: Display the previous stored videos from Firestore index
* Veo 2 settings/features: Aspect ratio, Duration, Auto prompt enhancer


Future featureset

* Prompt rewriter
* Additional Veo 2 features: seed, negative prompt, person generation control
* Advanced Veo 2 features


This is built using [Mesop](https://mesop-dev.github.io/mesop/) with [scaffold for Studio style apps](https://github.com/ghchinoy/studio-scaffold).


## Prerequisites

You'll need the following
* This source
* Google Cloud Storage bucket to store media
* Firestore database to store the index for the Library
* To run this locally, you'll also need a python virtual environment set up.
* Application environment variables set


### Source

For this experiment, download the source and then change to this directory

```bash
git clone https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git
cd vertex-ai-creative-studio/
git checkout veo
cd experiments/veo-app/
```

### Google Cloud Storage bucket

You'll need a Google Cloud Storage bucket to hold the videos created and images uploaded.

By default, if you don't specify a bucket name in one of the applicaiton environment variables below, it'll be "`YOUR_PROJECT_NAME`-assets".

You can create this like so:

```bash
export PROJECT_ID=$(gcloud config get project)
gcloud storage mb -l us-central gs://${PROJECT_ID}-assets
```

#### CORS Configuration

To allow the application to display images and other assets from your GCS bucket, you must configure Cross-Origin Resource Sharing (CORS) on the bucket. This is a security measure that tells the browser it's safe to load resources from a different domain.

1.  **Create a `cors.json` file** with the following content. This configuration allows access from your local development environment and your deployed Cloud Run services.

    ```json
    [
      {
        "origin": [
          "http://0.0.0.0:8080",
          "https://your-app-name-....run.app" 
        ],
        "method": ["GET"],
        "responseHeader": ["Content-Type"],
        "maxAgeSeconds": 3600
      }
    ]
    ```

2.  **Apply the configuration** to your bucket using the `gcloud` command-line tool:

    ```bash
    gcloud storage buckets update gs://your-bucket-name --cors-file=./cors.json
    ```

#### Troubleshooting CORS

If you are still seeing CORS errors in your browser's developer console after applying the configuration, you can verify the current CORS settings for your bucket with the following command:

```bash
gcloud storage buckets describe gs://your-bucket-name --format="json(cors_config)"
```

This will print the current CORS configuration. Ensure that your application's origin (e.g., `http://0.0.0.0:8080`) is listed in the `origin` array. Note that it may take a minute or two for the changes to propagate after you apply them.


### Cloud Firestore

We will be using [Cloud Firestore](https://firebase.google.com/docs/firestore), a NoSQL cloud database that is part of the Firebase ecosystem and built on Google Cloud infrastructure, to save generated video metadata for the Library.

> If you're new to Firebase, a great starting point is [here](https://firebase.google.com/docs/projects/learn-more#firebase-cloud-relationship).

Go to your Firebase project and create a database. Instructions on how to do this can be found [here](https://firebase.google.com/docs/firestore/quickstart).

Next do the following steps:

* Create a collection called `genmedia`. This is the default collection name. 

The name of the collection can be changed via environment variables in the `.env` file, by setting the environment variable `GENMEDIA_COLLECTIONS_NAME` to your chosen collection name.

Next, you'll need to create an index for the `timestamp` field. This will allow the library page to sort the media by the time it was created. You can create this index manually in the Google Cloud Console under Firestore > Indexes, or Firestore will prompt you to create it automatically the first time the query is run by the application.

Finally, you'll need to set up security rules to protect the data in your Firestore database. A good starting point is to ensure that only authenticated users can read or write documents, and they can only access documents that they created. You can paste the following rules into the "Rules" tab of your Firestore database in the Google Cloud Console:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Match any document in the 'genmedia' collection
    match /genmedia/{docId} {
      // Allow read and write access only if the user is authenticated
      // and their email matches the 'user_email' field in the document.
      allow read, write: if request.auth != null && request.auth.token.email == resource.data.user_email;
    }
  }
}
```



### Python virtual environment

A python virtual environment, with required packages installed.

Using the [uv](https://github.com/astral-sh/uv) virtual environment and package manager:

```
# sync the requirements to a virtual environment
uv sync
```

If you've done this before, you can also use the command `uv sync --upgrade` to check for any package version upgrades.


### Application Environment variables

Use the included dotenv.template and create a `.env` file with your specific environment variables. 

Only one environment variable is required:

* `PROJECT_ID` your Google Cloud Project ID, obtained via `gcloud config get project`


See the template dotenv.template file for the defaults and what environment variable options are available.



## GenMedia Creative Studio - v.next


### Running

Once you have your environment variables set, either on the command line or an in .env file:

```bash
uv run main.py
```


### Other ways of running

Use Cloud Shell and follow the tutorial instructions.


  [![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git&cloudshell_workspace=experiments/veo-app&cloudshell_tutorial=tutorial.md)


### Developing

Using the mesop app in a virtual environment provides the best debugging and building experience as it supports hot reload.

```bash
source .venv/bin/activate
```

Start the app, use the mesop command in your python virutal environment

```bash
mesop main.py
```

## Navigation

The application's side navigation is dynamically generated from the `config/navigation.json` file. This approach allows for easy updates to the navigation structure without modifying Python code.

### How it Works

When the application starts, it reads `config/navigation.json` and uses Pydantic models to validate the structure of the navigation items. This ensures that each entry has the required fields and correct data types, preventing runtime errors.

### Modifying the Navigation

To add, remove, or modify a navigation link, simply edit the `config/navigation.json` file. Each item in the `pages` list is a JSON object with the following structure:

*   `id` (required, integer): A unique identifier for the navigation item. The list is sorted by this value.
*   `display` (required, string): The text that will be displayed for the link.
*   `icon` (required, string): The name of the [Material Symbol](https://fonts.google.com/icons) to display.
*   `route` (optional, string): The application route to navigate to (e.g., `/home`).
*   `group` (optional, string): The group the item belongs to (e.g., `foundation`, `workflows`, `app`).
*   `align` (optional, string): Set to `bottom` to align the item to the bottom of the navigation panel.

### How to Control Navigation Items with Feature Flags

You can temporarily hide or show a navigation item by using a feature flag in `navigation.json` and controlling it via your `.env` file.

**1. Add the Feature Flag:**
First, add a `feature_flag` key to the item you want to control in `config/navigation.json`. Give it a descriptive name, for example:

```json
{
  "id": 40,
  "display": "Motion Portraits",
  "icon": "portrait",
  "route": "/motion_portraits",
  "group": "workflows",
  "feature_flag": "MOTION_PORTRAITS_ENABLED"
}
```

**2. Control Visibility via `.env` file:**
Now, you can control whether this item appears in the navigation by setting the `MOTION_PORTRAITS_ENABLED` variable in your `.env` file.

*   **To HIDE the page:** Either **do not** include `MOTION_PORTRAITS_ENABLED` in your `.env` file, or set it to `False`.
*   **To SHOW the page:** Add `MOTION_PORTRAITS_ENABLED=True` to your `.env` file.

The application will automatically show or hide the link when you restart it.



# Disclaimer

This is not an officially supported Google product.