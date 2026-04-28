---
title: 'Terraform Installation'
---

GenMedia Creative Studio can be easily deployed to Google Cloud using the provided Terraform configuration.

## Prerequisites
- [Terraform](https://www.terraform.io/downloads.html) installed
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed

## Deployment Steps

```bash
gcloud auth application-default login
terraform init
terraform plan
terraform apply
```