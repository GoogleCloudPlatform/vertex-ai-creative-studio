---
title: "Architecture & Solution Design"
---

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