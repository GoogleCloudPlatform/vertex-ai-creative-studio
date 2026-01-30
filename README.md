# GenMedia Creative Studio | Vertex AI

> ###### _This is not an officially supported Google product. This project is not eligible for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security). This project is intended for demonstration purposes only. It is not intended for use in a production environment._

![GenMedia Creative Studio v.next](https://github.com/user-attachments/assets/da5ad223-aa6e-413c-b36e-5d63e5d5b758)

![GenMedia Creative Studio v.next](https://github.com/user-attachments/assets/61977f3c-dbb6-4002-b8c0-77d57aa03cce)

## Table of Contents

- [GenMedia Creative Studio | Vertex AI](#genmedia-creative-studio--vertex-ai)
- [Table of Contents](#table-of-contents)
- [GenMedia Creative Studio](#genmedia-creative-studio)
  - [Experiments](#experiments)
- [Deploying GenMedia Creative Studio](#deploying-genmedia-creative-studio)
  - [Prerequisites](#prerequisites)
    - [1. Download the source code for this project](#1-download-the-source-code-for-this-project)
    - [2. Export Environment Variables](#2-export-environment-variables)
  - [Deploying with Custom Domain](#deploying-with-custom-domain)
    - [1. Initialize Terraform](#1-initialize-terraform)
    - [2. Create a DNS A record for the domain name](#2-create-a-dns-a-record-for-the-domain-name)
    - [3. Build and Deploy Container Image](#3-build-and-deploy-container-image)
    - [4. Wait for certificate to go to provisioned state](#4-wait-for-certificate-to-go-to-provisioned-state)
  - [Deploying using Cloud Run Domain](#deploying-using-cloud-run-domain)
    - [1. Initialize Terraform](#1-initialize-terraform-1)
    - [2. Build and Deploy Container Image](#2-build-and-deploy-container-image)
    - [3. Edit Cloud Run's IAP Policy to provide initial user's access](#3-edit-cloud-runs-iap-policy-to-provide-initial-users-access)
  - [Deploying to Cloud Shell for Testing](#deploying-to-cloud-shell-for-testing)
- [Adding Additional Users](#adding-additional-users)
- [Solution Design](#solution-design)
  - [Custom Domain Using Identity Aware Proxy w/Load Balancer](#custom-domain-using-identity-aware-proxy-wload-balancer)
  - [Cloud Run Domain Using Identity Aware Proxy w/Cloud Run](#cloud-run-domain-using-identity-aware-proxy-wcloud-run)
  - [Solution Components](#solution-components)
    - [Runtime Components](#runtime-components)
    - [Build time Components](#build-time-components)
  - [Setting up your development environment](#setting-up-your-development-environment)
    - [Python virtual environment](#python-virtual-environment)
    - [Application Environment variables](#application-environment-variables)
  - [GenMedia Creative Studio - Developing](#genmedia-creative-studio---developing)
    - [Running](#running)
    - [Developing](#developing)
  - [Contributing changes](#contributing-changes)
  - [Licensing](#licensing)
- [Disclaimer](#disclaimer)

## GenMedia Creative Studio

> **Browser Compatibility:** For the best experience, we recommend using Google Chrome. Some features may not work as expected on other browsers, such as Safari or Firefox.

GenMedia Creative Studio is a web application showcasing Google Cloud's generative media - Veo, Lyria, Chirp, Gemini 2.5 Flash Image Generation (nano-banana), and Gemini TTS along with custom workflows and techniques for creative exploration and inspiration. We're looking forward to see what you create!

Current featureset

- Image: Imagen 3, Imagen 4, Virtual Try-On, Gemini 2.5 Flash Image Generation
- Video: Veo 2, Veo 3
- Music: Lyria
- Speech: Chirp 3 HD, Gemini Text to Speech
- Workflows: Character Consistency, Shop the Look, Starter Pack Moodboard, Interior Designer
- Asset Library

This is built using [Mesop](https://mesop-dev.github.io/mesop/), an open source Python framework used at Google for rapid AI app development, and the [scaffold for Studio style apps](https://github.com/ghchinoy/studio-scaffold).

## Experiments

The [Experimental folder](./experiments/) contains a variety of stand-alone applications and new and upcoming features that showcase cutting-edge capabilities with generative AI.

Here's a glimpse of what you'll find:

**MCP Tools**

- **MCP Tools for Genmedia:** Model Context Protocol servers for Veo, Imagen, Lyria, Chirp, and Gemini to bring creativity to your agents.

**Combined Workflows**

- **Countdown Workflow:** An automated two-stage pipeline to create branded countdown videos.
- **Storycraft:** An AI-powered video storyboard generation platform that transforms text descriptions into complete video narratives.
    - **Creative GenMedia Workflow:** An end-to-end workflow to produce high-quality, on-brand creative media.
    - **Run, Veo, Run:** A real-time, multimodal video generation experiment that creates a branching narrative loop using Veo 3.1 for video extension and Gemini 3 for context awareness.

**Prompting Techniques**

- **Promptlandia:** A powerful web app to analyze, refine, and improve your prompts.
- **Veo Genetic Prompt Optimizer:** An automated system to evolve and refine high-level "metaprompts" for Veo.
- **Character & Item Consistency:** Workflows for maintaining consistency for characters and items across video scenes.

**Image Generation & Analysis**

- **Virtual Try-On:** A notebook for virtually trying on outfits at scale.
- **Imagen Product Recontextualization:** Tools for large-scale product image recontextualization.
- **Arena:** A visual arena for rating and comparing images from different models.

**Audio & Video**

- **Creative Podcast Assistant:** A notebook for creating a podcast with generative media.
- **Babel:** An experimental app for Chirp 3 HD voices.

...and much more! For a full, detailed list of all experiments, please see the [Experiments README](./experiments/README.md).

## 🤖 AI Assistants

This repository uses **Google's Gemini CLI** to automate software engineering tasks.

- **Code Reviewer:** Automatically reviews Pull Requests for bugs and security issues.
- **Issue Triage:** Automatically labels and categorizes new issues.
- **Maintainer Commands:** Allows maintainers to manually trigger reviews (`@gemini-cli /review`) or ask questions (`@gemini-cli Explain this...`).

For detailed documentation on the agents and workflows, see [AGENTS.md](./AGENTS.md).

## Deploying GenMedia Creative Studio

Deployment of GenMedia Creative Studio is accomplished using a combination of Terraform and Cloud Build. Terraform is used to deploy the infrastructure and Cloud Build is used to create the container image and update the Cloud Run service to use it.

You have two deployment options for this application:

1. [Deploy using a custom domain](#deploying-with-custom-domain). Use this if:
   - You need to support external identities. Included Terraform script does not support this; however, you can customize the script.
   - You prefer more control over the domain used
2. [Deploy using the autogenerated Cloud Run Domain](#deploying-using-cloud-run-domain). Use this if:
   - You can not create a DNS entry
   - [IAP for Cloud Run Known Limitations](https://cloud.google.com/iap/docs/enabling-cloud-run#known_limitations) are non-blockers (e.g., no external identities, no Cloud CDN support)

### Prerequisites

You'll need the following

- An existing Google Cloud Project
- If you want to use a custom domain, you need the ability to create a DNS A record for your target domain that resolves to the provisioned load balancer

### 1. Download the source code for this project

Download the source

```bash
git clone https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git
```

### 2. Export Environment Variables

The following environment variables are the minimum required to deploy the application.

- REGION - Should be set to `us-central1`. Prior to selecting a different region, validate the GenAI models needed are available [here](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#google_model_endpoint_locations).
- PROJECT_ID - Set to the desired Google Cloud project's ID, obtained via `gcloud` below or you can enter it manually.
- DOMAIN_NAME - Update with the DNS name to be used to reach the web application (e.g., creativestudio.example.com). A Google Cloud Managed certificate will be created for this domain.
- INITIAL_USER - Email address of initial user given access to the web application (e.g., <admin@example.com>)

Replace the example values and execute the script below:

```bash
export REGION=us-central1 PROJECT_ID=$(gcloud config get project) 
export INITIAL_USER=admin@example.com
```

## Deploying with Custom Domain

Follow these steps if you are going to deploy GenMedia Creative Studio using your own custom domain. You will need the ability to create a DNS A record if you choose this deployment option.

### 1. Initialize Terraform

Because you are using a custom domain, you will need to export one more variable with the DNS name for the domain that will be used to navigate to GenMedia Creative Studio.

```bash
export DOMAIN_NAME=creativestudio.example.com
```

Make sure your command line is in the folder containing this README (i.e., in the root of the main repository, /). Then create the `terraform.tfvars` using the following command:

```bash
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
initial_user = "$INITIAL_USER"
domain = "$DOMAIN_NAME"
EOF

terraform init
terraform apply
```

### 2. Create a DNS A record for the domain name

A load balancer and a Google Cloud managed certificate are provisioned by the Terraform configuration file. You must create a DNS A record that resolves to the IP address of the provisioned load balancer. Below is a sample output from running the `terraform apply` command, showing where the provisioned application balancer's IP is displayed.

![Load Balancer IP Address](https://github.com/user-attachments/assets/e9d6af9a-9445-441d-b89a-04b412f9baac)

If you use Google Cloud DNS, follow the steps [here](https://cloud.google.com/dns/docs/records). Provisioning a Google-managed certificate might take up to 60 minutes from the moment your DNS and load balancer configuration changes have propagated across the internet.

> If you take too long to create the A record, usually >15 minutes or the DNS entry resolves to any other IP address than the load balancer's, provisioning of the Google Cloud Managed certificate may fail with a status of `FAILED_NOT_VISIBLE`. If this is the case, make sure the DNS A record is updated correctly and follow the steps [here](https://cloud.google.com/load-balancing/docs/ssl-certificates/troubleshooting?#verify_configuration_changes).

### 3. Build and Deploy Container Image

A shell script, `build.sh`, is included in this repo that submits a build to Cloud Build which builds and deploys the application's container image. Use the following command:

```bash
./build.sh
```

### 4. Wait for certificate to go to provisioned state

With both the infrastructure and application deployed, you are just waiting for the certificate to complete provisioning. Once you see the status as "ACTIVE" and the "In use by" section populated (see sample below), your application is ready for use. You can navigate to the [Certificate Manager GCP Console page](https://console.cloud.google.com/security/ccm/list/lbCertificates), and select the certificate to keep an eye on the status.

![Provisioned Certificate](https://github.com/user-attachments/assets/20c0fb6b-c865-40e1-a9cc-fc3b0d349184)

## Deploying using Cloud Run Domain

If you are unable to create a DNS record in your corporate domain, you can also use the autogenerated Cloud Run domain along with it's preview support for IAP to secure the endpoint.

> Currently, Cloud Run's integration with IAP is a preview feature and is subject to the "Pre-GA Offerings Terms" in the General Service Terms section of the [Service Specific Terms](https://cloud.google.com/terms/service-terms#1). Pre-GA features are available "as is" and might have limited support. For more information, see the [launch stage descriptions](https://cloud.google.com/products#product-launch-stages).

### 1. Initialize Terraform

Make sure your command line is in the folder containing this README (i.e., in the root of the main repository, /). Then create the `terraform.tfvars` using the following command:

```bash
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
initial_user = "$INITIAL_USER"
use_lb = false
EOF

terraform init
terraform apply
```

Make sure to take note of the Cloud Run URL that is output. This is what you will navigate to in your browser to access the application. Before doing that though, you need to build and deploy the container image.

![Cloud Run URL output](https://github.com/user-attachments/assets/e8729bfb-151b-4cbc-9006-6f76f5ce713e)

### 2. Build and Deploy Container Image

A shell script, `build.sh`, is included in this repo that submits a build to Cloud Build which builds and deploys the application's container image. Use the following command:

```bash
./build.sh
```

### 3. Edit Cloud Run's IAP Policy to provide initial user's access

The last step is to change the IAP policy of the Cloud Run service to provide access to a user. You can also use a group but for the purposes of this example, a single user is given access.

```bash
gcloud beta iap web add-iam-policy-binding \
--project=$PROJECT_ID \
--region=$REGION \
--member=user:$INITIAL_USER \
--role=roles/iap.httpsResourceAccessor \
--resource-type=cloud-run \
--service=creative-studio
```

Congratulations, you can now navigate to the address provided in the `cloud-run-app-url` Terraform output.

## Deploying to Cloud Shell for Testing

Use this option if you want to quickly run the UI without having to setup a local development environment. To get started, use Cloud Shell and follow the tutorial instructions.

  [![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git&cloudshell_tutorial=tutorial.md)

# Updating GenMedia Creative Studio

As new features and fixes are added to GenMedia Creative Studio, you will want to update your deployment. You do **not** need to destroy your existing infrastructure.

## Updating Application Code

If you only need to update the application code (Python files, UI changes):

1. Pull the latest changes from the repository:

   ```bash
   git pull
   ```

2. Run the build script:

   ```bash
   ./build.sh
   ```

This script submits a new build to Cloud Build, creates a new container image, and updates the existing Cloud Run service.

## Updating Infrastructure

If the updates include changes to the Terraform configuration (e.g., new environment variables, new Google Cloud services):

1. Pull the latest changes:

   ```bash
   git pull
   ```

2. Initialize Terraform to download any new provider requirements:

   ```bash
   terraform init -upgrade
   ```

3. Apply the changes. Terraform will only update what has changed:

   ```bash
   terraform apply
   ```

# Adding Additional Users

With any of the deployment options above that use IAP, if you need to add additional users, there are two steps to take to make sure those users can both access the application and the images generated:

- Application Access - Add the user to IAP. Follow [these steps](https://cloud.google.com/iap/docs/managing-access#managing_access_console) if you deployed using a load balancer, granting the user the _IAP-Secured Web App User_ role. If you deployed using only the Cloud Run provided URL, follow [these steps](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access).
- Image Access - The images are served using the authenticated GCS URL of each storage object so users need to be granted the _Storage Object Viewer_ role. The name of the bucket is available as the `assets-bucket` Terraform output.

> **Note:** For the application to function correctly, the **Cloud Run service account** must have the **`Storage Object Viewer`** (`roles/storage.objectViewer`) role on the GCS bucket. This allows the application to read media assets and serve them to users through the proxy.

# Frequently Asked Questions

For common questions and troubleshooting tips, please refer to the [FAQ](FAQ.md).

# Solution Design

There are two way to deploy this solution. One using a custom domain with a load balancer and IAP integration. The other is using Cloud Run's default URL and integrating IAP with Cloud Run. The below diagrams depict the components used for each option.

## Custom Domain Using Identity Aware Proxy w/Load Balancer

![Solution Design - LB IAP](https://github.com/user-attachments/assets/ad057afb-4d7c-4857-b074-427eccbfaaa0)

## Cloud Run Domain Using Identity Aware Proxy w/Cloud Run

![Solution Design - Cloud Run IAP](https://github.com/user-attachments/assets/ec2c1e04-6890-4246-b134-9923955c0486)

The above diagram depicts the components that make up the Creative Studio solution. Items of note:

- DNS entry _is not_ deployed as part of the provided Terraform configuration files. You will need to create a DNS A record that resolves to the IP address of the provisioned load balancer so that certificate provisioning succeeds.
- Users are authenticated with Google Accounts and access is [managed through Identity Aware Proxy (IAP)](https://cloud.google.com/iap/docs/managing-access). IAP does support external identities and you can learn more [here](https://cloud.google.com/iap/docs/enable-external-identities).

## Solution Components

### Runtime Components

- [Load Balancer](https://cloud.google.com/load-balancing) - Provides the HTTP access to the Cloud Run hosted application

- [Identity Aware Proxy](https://cloud.google.com/security/products/iap) - Limits access to web application for only authenticated users or groups
- [Cloud Run](https://cloud.google.com/run) - Serverless container runtime used to host Mesop application
- [Cloud Firestore](https://firebase.google.com/docs/firestore) - Data store for the image / video / audio metadata. If you're new to Firebase, a great starting point is [here](https://firebase.google.com/docs/projects/learn-more#firebase-cloud-relationship).
- [Cloud Storage](https://cloud.google.com/storage) - A bucket is used to store the image / video / audio files

### Build time Components

- [Cloud Build](https://cloud.google.com/build) - Uses build packs to create the container images, push them to Artifact Registry and update the Cloud Run service to use the latest image version. To simplify deployment, connections to a GitHub project and triggers are not deployed w/Terraform. The source code that was cloned locally is compressed and pushed to Cloud Storage. It is this snapshot of the source that is used to build the container image.

- [Artifact Registry](https://cloud.google.com/artifact-registry/docs/overview) - Used to store the container images for the web aplication
- [Cloud Storage](https://cloud.google.com/storage) - A bucket is used to store a compressed file of the source used for the build

## Setting up your development environment

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

- `PROJECT_ID` your Google Cloud Project ID, obtained via `gcloud config get project`

See the template dotenv.template file for the defaults and what environment variable options are available.

## GenMedia Creative Studio - Developing

### Running

Once you have your environment variables set, either on the command line or an in .env file:

```bash
uv run main.py
```

### Developing

Please see the [Developer's Guide](./developers_guide.md) for more information on how this application was built, including specific information about [Mesop](https://mesop-dev.github.io/mesop/) and the [scaffold for Studio style apps](https://github.com/ghchinoy/studio-scaffold).

When developing this app, since it's a FastAPI application that serves Mesop, please use the following

```bash
uv run main.py
```

Traditional Mesop hot reload capabilities (i.e. `mesop main.py`) are not fully available at this time.

## Contributing changes

Interested in contributing? Please open an issue describing the intended change. Additionally, bug fixes are welcome, either as pull requests or as GitHub issues.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## Licensing

Code in this repository is licensed under the Apache 2.0. See [LICENSE](LICENSE).

# Disclaimer

This is not an officially supported Google product. This project is not eligible for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security).