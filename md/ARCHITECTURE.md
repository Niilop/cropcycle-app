# Implemented architecture

This describes what exists now: the CropCycle backend from [plan 002](plans/002-crop-rotation-mvp.md) Phases 1–2 (domain, scoring and auto-layout), and the template's web frontend trimmed to a sign-in and gardens shell. The Expo app is planned (Phases 3–5).

## Components and request flow

```text
Browser: React + TypeScript (temporary web shell)
  -> /api/* through Vite (development) or Nginx (Docker)
  -> FastAPI routes (proxy removes /api)
  -> owner-scoped dependencies (backend/api/dependencies.py)
  -> service functions (raise DomainError -> 404/409/422)
       layout_service: DB -> plain dataclasses -> services/layout (pure scoring + solver)
  -> SQLAlchemy session
  -> external PostgreSQL

Seed loader (python -m backend.seed) -> catalogue tables
```

Development uses frontend port 5173 and backend port 8000. `make dev` checks setup and starts both servers with shared shutdown. In Docker, Nginx serves the built frontend and proxies to the backend. Migrations (`make migrate`) and catalogue seeding (`make seed`) are explicit steps before normal startup.

| Location | Responsibility |
| --- | --- |
| [backend/main.py](../backend/main.py) | App creation, router registration, domain-error mapping, CORS, liveness and readiness |
| [backend/api/endpoints/](../backend/api/endpoints/) | `auth`, `catalog` (read-only), `gardens` (gardens, beds, history), `plans` (plans, requested crops, placements) |
| [backend/api/dependencies.py](../backend/api/dependencies.py) | Owner-scoped lookups for gardens, beds, plantings, plans and placements; write rate limit |
| [backend/services/](../backend/services/) | Authentication, garden/bed/history logic, plan logic (including **Fill remaining**), catalogue reads, window helpers, error types |
| [backend/services/layout/](../backend/services/layout/) | Pure scoring (`scoring.py`) and layout search (`solver.py`) over dataclasses (`model.py`); no database access (D008) |
| [backend/services/layout_service.py](../backend/services/layout_service.py) | Loads a plan's context (active beds, the last 10 years of history, the previous and next years' draft plans, the catalogue) for the layout package |
| [backend/seed/](../backend/seed/) | `catalog.json` (families, crops, rotation and companion rules in en/fi) and its validating, idempotent loader |
| [backend/models/](../backend/models/) | SQLAlchemy models and Pydantic request/response schemas, including the `YearMonth` type |
| [backend/alembic/](../backend/alembic/) | Versioned database changes; `0003_crop_domain` introduces the domain |
| [frontend/src/](../frontend/src/) | Web shell: overview, register/login, account, gardens list and create |
| [tests/](../tests/) and [frontend/tests/](../frontend/tests/) | Backend tests (SQLite, real seed data) and mocked browser tests |
| [frontend/e2e/](../frontend/e2e/) and [compose.smoke.yaml](../compose.smoke.yaml) | Real browser-to-database smoke test with a disposable, seeded PostgreSQL |

## Data and authorization

```text
User 1─* Garden 1─* Bed 1─* Planting *─1 Crop *─1 CropFamily
             1─* Plan 1─* PlannedCrop *─1 Crop
                     1─* PlanPlacement *─1 Bed, Crop
Planting.plan_id ─> Plan (set when a plan is completed; SET NULL on plan delete)
RotationRule ─> Crop xor CropFamily;  CompanionRule ─> (Crop a < Crop b)
```

- **Shared catalogue** (families, crops, rules): readable by any signed-in user and written only by the seed loader, which upserts by `slug` (D007). Crops and families missing from the file are kept; rules are synced to the file.
- **Private data** is owned through `Garden.user_id`. Every lookup joins to the garden owner, and foreign or missing records return 404. References in request bodies (a crop, a bed from another garden, or a garden in `POST /plans`) return 422 `Unknown …`.
- **Deletes:** deleting a garden cascades in the database to its beds, plantings, plans and placements. `DELETE /beds/{id}` only sets `archived_at`: archived beds are hidden from the garden view and reject new placements (409), but keep their history. Deleting a plan keeps the plantings it wrote.
- **Windows** (D012): `start_month`/`end_month` are first-of-month `DATE` columns, exchanged as `"YYYY-MM"`, with `start <= end` and at most 24 months. Omitted windows come from the crop's defaults (`backend/services/windows.py`). A planting's `year` must be inside its window; a placement must touch its plan's year.
- **Plans:** there is one per garden and year. Placements created or edited through the API become `source=manual`, locked by default. Removing a requested crop removes its placements. `complete` replaces the plantings this plan previously wrote with one per placement and makes the plan read-only (409 on edits) until `reopen`.
- Rotation, companion and overlap concerns are never enforced (D009). Overlapping plantings and placements are accepted.

## Scoring and auto-layout

- **Score (0–100):**
  - The base is 35% same-crop rotation, 45% family rotation and 20% timing. Gaps are measured against crop, then family, then default (3-year) rules; each rule's weight makes its penalty harsher.
  - Neighbours add +5 (positive) or −10 (negative) points per companion weight, capped at +10 and −20. Beds count as neighbours within 1.0 m edge to edge, when their seasons overlap.
  - Bands: ≥80 very suitable, ≥60 suitable, ≥40 possible, otherwise some considerations. A timing overlap of two or more months beyond the handover month gives `no_free_season`.
- **Context:**
  - Rotation looks at history and occupants up to the plan year, including this year's earlier crops in the bed.
  - Timing looks at every occupant of the bed: history, this plan's placements, and the adjacent years' draft plans. Completed plans are represented by the history they wrote.
- **Fill remaining** (`POST /plans/{id}/generate-layout`):
  - It deletes only suggested, unlocked placements, computes the demand still unmet, and runs greedy placement (most constrained first), then insert, move and swap improvement within 1 s.
  - Layouts are ranked by crops placed, then total score. Suggestions use the crop's default window, never clash in timing, and never repeat a crop in a bed within the year.
  - Demand that can't be placed is returned as `unplaced`.
- **Suitability** (`GET /plans/{id}/suitability?crop_id=`) assesses a new placement of the crop in every active bed, given the current plan. Plan details carry a fresh `assessment` for each placement in an active bed.
- Registration hashes passwords with Argon2. Login returns an HS256 JWT, valid for 30 days by default (D006). The web shell keeps it in memory; the mobile app will use secure storage.

## Persistence and contracts

`get_db` supplies a session per request. Services commit mutations; the dependency closes the session. ORM models define storage; Pydantic schemas define the HTTP contract. Constraint names follow the naming convention on `Base.metadata`. The web shell's TypeScript types are maintained by hand; the mobile app will generate them from OpenAPI (D010).

## Current limits

- Rate limits use process-local memory. Multiple workers would need shared rate-limit storage (D013).
- Persistent refresh tokens, revocation, password reset and closing self-registration are not implemented.
- `/health` checks process liveness; `/ready` checks a database query, not migration or seed status.
- Browser tests mock the API. The smoke test covers the real stack through Nginx but is not exhaustive.
