# GitHub Actions Workflow Fix Report

**Date:** December 8, 2025
**Topic:** Resolving "Unrecognized named-value: 'secrets'" in Reusable Workflows

## 🔴 The Issue

Recent GitHub Actions runs failed with the error:
`Invalid workflow file: .github/workflows/gemini-triage.yml#L56: Unrecognized named-value: 'secrets'`

### Root Cause

The project uses **Reusable Workflows** (triggered via `workflow_call`).

- The caller workflow (`gemini-dispatch.yml`) correctly passed secrets using `secrets: inherit`.
- However, the *called* workflows (`gemini-triage.yml`, etc.) referenced `secrets.GEMINI_API_KEY` inside their steps without explicitly declaring that they expect to receive these secrets in their `workflow_call` configuration.
- GitHub's strict workflow validator failed because it could not verify that `secrets` would be available in the context of the called workflow at parse time.

## 🟢 The Solution

We updated the reusable workflows to explicitly define the secrets they require. This satisfies the schema validation and ensures the secrets are accessible.

### Affected Files

1. `.github/workflows/gemini-triage.yml`
2. `.github/workflows/gemini-review.yml`
3. `.github/workflows/gemini-invoke.yml`

### Changes Applied

In each file, the `on: workflow_call` section was updated to include a `secrets` block:

```yaml
on:
  workflow_call:
    inputs:
      additional_context:
        type: 'string'
        description: 'Any additional context from the request'
        required: false
    # ADDED: Explicit definition of required secrets
    secrets:
      GEMINI_API_KEY:
        required: true
      GOOGLE_API_KEY:
        required: true
      APP_PRIVATE_KEY:
        required: true
```

## Verification

This change ensures that:

1. The workflow syntax is valid.
2. The `secrets` object is correctly populated when the workflow runs.
3. The dispatch workflow can successfully pass these secrets down to the child workflows.
