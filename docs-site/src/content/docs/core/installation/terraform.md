---
title: 'Terraform Installation'
---

GenMedia Creative Studio can be easily deployed to Google Cloud using the provided Terraform configuration.

## Prerequisites
- [Terraform](https://www.terraform.io/downloads.html) installed
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed

## Deployment Steps

The Cloud Run Terraform root lives in `deploy/terraform/cloudrun`. Run the
commands from that directory:

```bash
gcloud auth application-default login
cd deploy/terraform/cloudrun
terraform init
terraform plan
terraform apply
```

## Deploying to multiple projects / environments

Service accounts are created at **project scope**, so the same `account_id` (e.g., `service-creative-studio`) yields a distinct SA per project — there is no cross-project name collision at the GCP level. What must be isolated is **Terraform state**.

The GCS backend in `deploy/terraform/cloudrun/backend.tf` uses a fixed `prefix = "creative-studio/prod"`. If you reuse the same state bucket **and** prefix for two projects, both deployments share state and one will apply against the other project's resources (for example, an `iam.serviceaccounts.actAs` denial referencing an SA in a different project).

To deploy into multiple projects, isolate the state per environment using any one of:

- A **different state bucket** per project (`terraform init -backend-config="bucket=..."`), or
- A **different `prefix`** per project (`terraform init -backend-config="prefix=creative-studio/<env>"`), or
- Separate **Terraform workspaces** (`terraform workspace new <env>`).
