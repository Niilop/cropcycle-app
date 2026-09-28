# Current development status

## Current state

CropCycle's backend is implemented and merged to `main` ([PR #9](https://github.com/Niilop/cropcycle-app/pull/9) domain, [PR #10](https://github.com/Niilop/cropcycle-app/pull/10) scoring and **Fill remaining**; CI green). It provides:

- a seeded en/fi crop catalogue;
- owner-scoped gardens, beds (archived rather than deleted) and planting history, with windows that can cross the new year;
- yearly plans with requested crops, locked manual placements, and completion into history;
- rotation, family, neighbour and timing scoring with suitability bands, and whole-plan **Fill remaining** that never changes manual or locked choices.

The template's example features are removed. The Vite web frontend is a temporary sign-in and gardens shell. The Expo app is not built yet.

## Active work

[002 — Crop rotation planner MVP](plans/002-crop-rotation-mvp.md): Phases 1–2 are complete and merged. Phase 3 (Expo app foundation) is next. Crop data review is deferred until after the MVP (see [PROJECT.md](PROJECT.md#later-crop-data-quality)).

## Blockers and open questions

There are no product blockers. Locally, Docker is unavailable in this WSL distro, so `make smoke` (Nginx) and the PostgreSQL 18 checks rely on CI; they pass for Phase 1. Git pushes over SSH need a passphrase prompt that non-interactive sessions can't show, so pushes use the `gh` token over HTTPS. The hosting provider and distribution channel remain open until Phase 5.

## Validation reference

See [plan 002 validation results](plans/002-crop-rotation-mvp.md#validation-results).

## Next step

Scaffold `mobile/` (Phase 3), which adds the Expo and React Native npm dependencies listed in the plan's handoff. Start with web-build viewing, then the Android emulator and Expo Go on devices (see the device-testing notes in the plan).
