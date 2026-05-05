---
title: "Changelog & Notices"
---

Stay up-to-date with the latest releases, upcoming breaking changes, and major architectural improvements to GenMedia Creative Studio.

## ⚠️ Upcoming Developer Notices

### Planned Git History Scrub (Target: End of Month)
**Impact:** High (Requires local branch resets)

To significantly reduce repository clone times and CI overhead, we will be using `git-filter-repo` to scrub accidentally committed compiled binaries (approx. 300MB) from the repository's deep history. 

This operation will rewrite the commit hashes on the `main` branch. 

**What you will need to do when this happens:**
If you have an active local branch or PR, you will need to rebase your work onto the new `upstream/main`. Detailed instructions will be provided in the #engineering channel when the scrub occurs.

## Recent Updates

### Starlight Documentation Hub (May 2026)
* **Docs:** Migrated all deployment guides, architecture diagrams, and MCP tool instructions to a centralized Starlight (Astro) documentation hub.
* **UI:** Streamlined the root `README.md` to serve as a clean landing page pointing to the new docs.
