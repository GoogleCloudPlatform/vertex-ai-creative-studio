# Frequently Asked Questions (FAQ)

## Configuration & Deployment

### Q: Can I pass a list of users or a group to the `initial_user` Terraform variable for IAP access?

**A:** No, not by default.  The `initial_user` variable currently accepts only a single string (e.g., one email address). This is defined in `variables.tf` and used in `main.tf` with a hardcoded `user:` prefix.

To grant IAP access to multiple users or a group, you have two options:

#### Option 1: Use the Google Cloud Console (Recommended)
After deployment, you can manage access policies directly in the [Google Cloud Console > IAP](https://console.cloud.google.com/security/iap). This avoids modifying the Terraform code.

#### Option 2: Modify Terraform for Multiple Users
If you prefer to manage this via Terraform, you can modify the code to accept a list of users.

**1. Update `variables.tf`**
Change the `initial_user` variable to a list (or create a new variable like `additional_users`):

```hcl
variable "allowed_users" {
  description = "List of email addresses to grant IAP access"
  type        = list(string)
  default     = []
}
```

**2. Update `main.tf`**
Replace the existing `google_iap_web_iam_member` resource (or add a new one) to iterate over the list:

```hcl
resource "google_iap_web_iam_member" "multi_user_iap_access" {
  for_each = toset(var.allowed_users)
  
  project = var.project_id
  role    = "roles/iap.httpsResourceAccessor"
  member  = "user:${each.value}"
}
```

#### Option 3: Support Google Groups
The current `main.tf` hardcodes the `user:` prefix:
```hcl
member = "user:${var.initial_user}"
```

To support a Google Group, you must modify `main.tf` to use the `group:` prefix or make the prefix dynamic:

```hcl
variable "access_group" {
  description = "Google Group email for IAP access"
  type        = string
}

resource "google_iap_web_iam_member" "group_iap_access" {
  project = var.project_id
  role    = "roles/iap.httpsResourceAccessor"
  member  = "group:${var.access_group}"
}
```

For more details on available configuration options and environment variables, please refer to [Environment Variables](environment_variables.md).

### Q: The application works, but I'm not able to see images?

**A:** If the application UI loads but images (or other media assets) are failing to display, this is usually due to one of two reasons:

**1. Missing Permissions on the Cloud Run Service Account**
The Cloud Run service account must have permission to read objects from the Google Cloud Storage bucket where assets are stored. 
*   **Check:** Ensure the service account used by Cloud Run (e.g., `service-creative-studio@...`) has the **`Storage Object Viewer`** role (`roles/storage.objectViewer`) on the `GENMEDIA_BUCKET` (typically `creative-studio-{project_id}-assets`).
*   **Fix:** You can grant this role via the Google Cloud Console or using `gcloud`:
    ```bash
    gcloud storage buckets add-iam-policy-binding gs://<YOUR_ASSET_BUCKET> \
        --member=serviceAccount:<YOUR_SERVICE_ACCOUNT_EMAIL> \
        --role=roles/storage.objectViewer
    ```

**2. `USE_MEDIA_PROXY` Configuration**
By default, the application is configured to proxy media requests through the backend (`USE_MEDIA_PROXY=true`).
*   **If `true` (Default):** The browser requests images from the application server (`/proxy/image?...`), which then fetches them from GCS. This requires the **Service Account** to have GCS access (as described above). This is the recommended setup as it avoids CORS issues.
*   **If `false`:** The browser attempts to fetch images directly from the GCS bucket URL (`https://storage.googleapis.com/...`). This requires the bucket to be publicly accessible (not recommended) or the user's browser to have a valid authenticated session with Google that grants access to the bucket, AND the bucket must have a proper **CORS policy** configured to allow requests from your application's domain.