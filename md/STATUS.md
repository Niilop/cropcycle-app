# Current development status

## Current state

CropCycle's backend domain is implemented on branch `feat/phase1-backend-domain` (not yet pushed or merged):

- a seeded en/fi crop catalogue;
- owner-scoped gardens, beds (archived rather than deleted) and planting history, with windows that can cross the new year;
- yearly plans with requested crops, locked manual placements, and completion into history.

The template's example features are removed. The Vite web frontend is a temporary sign-in and gardens shell. Scoring, **Fill remaining** and the Expo app are not built yet.

## Active work

[002 — Crop rotation planner MVP](plans/002-crop-rotation-mvp.md): Phase 1 is complete and awaiting review. Phase 2 (scoring and auto-layout) is next.

## Blockers and open questions

There are no product blockers. Locally, Docker is unavailable in this WSL distro, so `make smoke` (Nginx) and the PostgreSQL 18 checks rely on CI. Equivalent checks passed on embedded PostgreSQL 16 (see the plan's validation results). The hosting provider and distribution channel remain open until Phase 5.

## Validation reference

See [plan 002 validation results](plans/002-crop-rotation-mvp.md#validation-results) for the Phase 1 working tree.

## Next step

Push `feat/phase1-backend-domain` and open a PR so CI runs. Then begin Phase 2 with the pure `backend/services/layout/` module and its unit tests.
