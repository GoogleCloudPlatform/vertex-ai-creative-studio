# How to Update Your Branch with Upstream Main

This document describes the steps to update your local working branch with the latest changes from the `upstream/main` branch.

1.  **Ensure your local changes are committed:** Before you can merge the latest upstream changes, you need to make sure that your own changes are committed. You can do this by running:

    ```bash
    git status
    ```

    If you have any uncommitted changes, you can add and commit them:

    ```bash
    git add .
    git commit -m "Your commit message"
    ```

2.  **Fetch the latest upstream changes:**

    ```bash
    git fetch upstream
    ```

3.  **Merge the upstream main branch into your current branch:**

    ```bash
    git merge upstream/main
    ```

4.  **Build and deploy the application:**

    ```bash
    ./build.sh
    ```

5.  **Examine the Terraform changes (if any):**

    ```bash
    terraform plan --out tf.plan
    ```

6. **Explain the Plan to the user and wait for confirmation**

    ```bash
    terraform apply
    ```

