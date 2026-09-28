# Project context

## Current purpose

CropCycle is a mobile-first crop rotation planner for home and allotment gardeners. Users draw their garden beds, record what grew where in past years, list what they want to grow next season, place the crops they care about, and let the app fill the rest using rotation history, crop families, neighbour compatibility, and seasonal timing.

Core principle: **the user chooses first; the app optimizes around those choices.** The app gives guidance only and never blocks an ordinary planting choice.

The source statement is [requirements/mvp-v0.md](requirements/mvp-v0.md). Implementation choices that refine it are in [DECISIONS.md](DECISIONS.md) (D005 onward).

## Users and first deliverable

- Users: individual gardeners managing one or more gardens on a tablet (primary) or phone.
- First deliverable: an Expo app (iOS, Android; web build for development and tests) backed by the existing FastAPI/PostgreSQL service. It meets the 12 success criteria in the requirements, tracked in [plan 002](plans/002-crop-rotation-mvp.md).
- Later: the same backend should support more clients, shared/custom crop catalogues, partial-bed plantings, and a stronger layout solver without data migration rework.

## Included scope (MVP)

- Account sign-in that persists on the device. Finnish and English UI.
- Gardens with rectangular beds that can be moved, resized, renamed, and archived.
- Planting history per bed, with several sequential crops per year.
- Yearly plans: requested crops and quantities, manual (locked) placements, and **Fill remaining** auto-layout.
- Per-bed suitability for a selected crop, shown as four gentle bands with short reason codes.
- A seeded catalogue of about 40 crops, their families, rotation rules, and companion rules, all stored as backend data.

## Boundaries

Out of scope for the MVP: mixed crops within one bed at the same time, graphical bed subdivision, weather, fertilizer, watering, harvest/yield, seed inventory, disease prediction, AI or chat features, social features, OR-Tools or other complex optimizers, and offline editing. The data model keeps `coverage` so that partial beds can be added later.

## Data ownership

- Private: gardens, beds, plantings, plans, planned crops, and placements. These are owned through `garden.user_id`. Foreign or missing records return 404.
- Shared, read-only to users: crop families, crops, rotation rules, and companion rules. They change only through versioned seed data (D007).

## Constraints

- Backend: the existing FastAPI, SQLAlchemy, Alembic, and Pydantic stack with `uv` and Ruff. Frontend: Expo with TypeScript and npm.
- Agronomic rules live in backend data, never in mobile code.
- Layout generation is synchronous and deterministic, and must finish within a couple of seconds for gardens of up to about 50 beds.
- Development runs on WSL2. Testing on a physical device needs Expo tunnel or LAN mirroring (see plan 002).

## Product answers (2026-09-28)

- Hosting is open. The app is for personal use first but must be able to host more users later: it runs as a portable container with PostgreSQL (D013).
- UI languages are Finnish and English. Catalogue names are stored in both (D014).
- Completing a plan copies its placements into planting history.
- Crops that occupy a bed across the new year, such as autumn-planted garlic, must be modelled so that they reserve the bed during that time (D012).

## Later: crop data quality

The seed catalogue is accepted as the MVP baseline. The owner wrote its values from general horticultural knowledge; they are not from a sourced database.
- Families are reliable, and rotation gaps are standard advice.
- Growing months are rough southern and central Finland estimates.
- Companion pairs are weakly evidenced, so their effect on scores is capped.

After the MVP, review better sources: Finnish sowing calendars, Puutarhaliitto, Luke, and openly licensed crop datasets (check licences before importing). Possible additions: regional windows, a nutrient-demand (feeding) rotation group, perennials, and green manure. Changes go through `catalog.json` and `make seed` (D007).

## Open product questions

- The concrete hosting provider and app distribution channel (EAS builds, TestFlight, Play internal testing) can wait until Phase 5.
