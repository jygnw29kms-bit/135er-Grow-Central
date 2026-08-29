# 135er-Grow Central · Canonical Naming

This repository has one canonical product and project identity:

- Product name: **135er-Grow Central**
- Short product name: **Grow Central**
- UI family: **GrowCentral Nexus UI**
- Technical slug: **grow-central**
- Repository: **135er-Grow-Central**
- Linux services/packages/paths: use the existing **grow-central** / **growcentral** conventions defined by the current codebase.

Legacy project names are not valid aliases and must not be reintroduced in source code, documentation, UI text, scripts, CI configuration, package metadata, filenames, branch names for new work, release names, artifacts, websites or deployment documentation.

The canonical naming guard in `tests/test_canonical_naming.py` blocks legacy `Grow + Control` naming variants in the current tracked tree.
