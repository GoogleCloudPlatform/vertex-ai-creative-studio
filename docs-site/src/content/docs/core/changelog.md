---
title: "Changelog & Notices"
---

Stay up-to-date with the latest releases, upcoming breaking changes, and major architectural improvements to GenMedia Creative Studio.

## ⚠️ Developer Notices & Action Items

### ✅ Git History Scrub Completed (August 2026)
**Impact:** High (Requires local branch resets for existing clones)

We have completed a repository-wide Git history scrub using `git-filter-repo` to remove historical compiled Go binaries and large orphaned media assets, reducing repository clone size by **~60% (from ~400MB to ~160MB)**.

Because this operation rewrote historical commit hashes on `main`, existing local clones will fail to pull normally due to diverged commit histories.

#### 🛠️ Instructions for Existing Clones

##### Option 1: Fast Reset (No uncommitted local changes)
If you have no uncommitted local work:
```bash
git fetch origin
git checkout main
git reset --hard origin/main
git clean -fd
```

##### Option 2: Fresh Clone (Recommended for a clean slate)
The easiest way to get the smaller packfile size immediately:
```bash
git clone git@github.com:GoogleCloudPlatform/vertex-ai-creative-studio.git
```

##### Option 3: Preserving In-Flight Feature Branches
If you have an active local feature branch with unmerged commits:
1. Rebase your feature branch commits onto the new `origin/main`:
   ```bash
   git fetch origin
   git rebase --onto origin/main <old-base-commit> <your-feature-branch>
   ```
2. Or cherry-pick your work onto a fresh branch cut from new `origin/main`:
   ```bash
   git checkout -b my-feature-branch-rebased origin/main
   git cherry-pick <your-commit-shas>
   ```

## Recent Updates

### Starlight Documentation Hub (May 2026)
* **Docs:** Migrated all deployment guides, architecture diagrams, and MCP tool instructions to a centralized Starlight (Astro) documentation hub.
* **UI:** Streamlined the root `README.md` to serve as a clean landing page pointing to the new docs.

