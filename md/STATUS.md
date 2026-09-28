# Current development status

## Current state

CropCycle's backend is implemented and merged to `main` ([PR #9](https://github.com/Niilop/cropcycle-app/pull/9) domain, [PR #10](https://github.com/Niilop/cropcycle-app/pull/10) scoring and **Fill remaining**; CI green). It provides:

- a seeded en/fi crop catalogue;
- owner-scoped gardens, beds (archived rather than deleted) and planting history, with windows that can cross the new year;
- yearly plans with requested crops, locked manual placements, and completion into history;
- rotation, family, neighbour and timing scoring with suitability bands, and whole-plan **Fill remaining** that never changes manual or locked choices.

The Expo app (`mobile/`, Phase 3) is on branch `feat/phase3-mobile`. It covers sign-in, gardens, a to-scale bed layout editor, planting history with season timelines, and a history view, in Finnish and English, on tablet and phone layouts. The Plan tab is a placeholder until Phase 4. The Vite web frontend is a temporary shell until Phase 5.

## Active work

[002 — Crop rotation planner MVP](plans/002-crop-rotation-mvp.md): Phases 1–2 are merged. Phase 3 (Expo app foundation) is complete and awaiting review. Phase 4 (planning screens) is next. Crop data review is deferred until after the MVP (see [PROJECT.md](PROJECT.md#later-crop-data-quality)).

## Blockers and open questions

There are no product blockers. Locally, Docker is unavailable in this WSL distro, so `make smoke` (Nginx) and the PostgreSQL 18 checks rely on CI; they pass for Phase 1. Git pushes over SSH need a passphrase prompt that non-interactive sessions can't show, so pushes use the `gh` token over HTTPS. The Phase 3 app has run on a phone through Expo Go over WSL mirrored networking (2026-09-28): sign-in and the basic functions work. The UI is menu-heavy; that is accepted for the MVP, and simplifying it is post-MVP work (see [PROJECT.md](PROJECT.md#later-ease-of-use)). The hosting provider and distribution channel remain open until Phase 5.

## Validation reference

See [plan 002 validation results](plans/002-crop-rotation-mvp.md#validation-results).

## Next step

Open the Phase 3 PR. Then start Phase 4: the Plan tab, the crop picker, suitability colours on the garden canvas, tap to place, and **Fill remaining**. To try the app, see [mobile/README.md](../mobile/README.md). Add `CORS_ORIGINS=http://localhost:8081` to your `.env` for the browser view.
