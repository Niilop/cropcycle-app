# 002 — Crop rotation planner MVP

- Status: active (Phase 1 complete, pending review; Phase 2 next)
- Updated: 2026-09-28
- Branch / PR: `feat/phase1-backend-domain`
- Related decisions: [D005–D014](../DECISIONS.md)
- Source: [requirements v0](../requirements/mvp-v0.md)

## Goal

Replace the template's example domain with the crop rotation planner so that a user can meet all 12 [success criteria](../requirements/mvp-v0.md#12-mvp-success-criteria) on iOS and Android. The user places the crops they care about, and the app fills the rest.

## Scope

- Included: the requirements v0 scope, refined by the design below and D005–D011. Additions that the requirements need but do not list:
  - a suitability endpoint for colour-coding beds;
  - bed archiving instead of hard deletion;
  - persistent mobile sign-in.
- Deferred: everything listed in requirements §11, plus offline editing, user-defined crops, localisation beyond centralized English strings, push notifications, and app-store release.
- Assumptions:
  - Existing template authentication is enough for "minimal auth". `User.username` serves as the name.
  - A single user edits a garden at a time, so there is no collaborative conflict handling. Last write wins.

## Design

### Data model (backend)

Units are metres in a garden-local plane, with the origin at top-left. Windows are `start_month`/`end_month` year-month values (`"YYYY-MM"` in the API, first-of-month `DATE` in the database) with `start <= end`, spanning at most 24 months (D012).

| Table | Key fields and rules |
| --- | --- |
| `gardens` | `user_id`, `name` (the canvas size is derived from the beds) |
| `beds` | `garden_id`, `name`, `x`, `y`, `width`, `height` (>0), `archived_at` nullable. `DELETE /beds/{id}` archives the bed. Archived beds are hidden from layout and scoring but keep their history. |
| `crop_families` | `slug` unique, `names` JSON `{en, fi}` |
| `crops` | `slug` unique, `names`, `family_id`, `default_start_month`, `default_end_month` (1–12), `default_start_year_offset` (-1 or 0) |
| `rotation_rules` | exactly one of `crop_id`/`family_id` set (check constraint), `preferred_gap_years`, `weight` |
| `companion_rules` | `crop_a_id < crop_b_id` (normalized, unique pair), `compatibility` enum, `weight` |
| `plantings` | `bed_id`, `crop_id`, `year` (season year, inside the window), window, `coverage` default 1.0 (not writable yet), `plan_id` nullable (set when created by completing a plan; `SET NULL` when the plan is deleted) |
| `plans` | `garden_id`, `year` (unique per garden), `name`, `status` (`draft`/`completed`) |
| `planned_crops` | `plan_id`, `crop_id` unique per plan, `quantity >= 1` |
| `plan_placements` | `plan_id`, `bed_id`, `crop_id`, window (must overlap the plan year), `locked`, `source` (`manual`/`suggested`); Phase 2 adds `score` and `reasons` |

Crop, family, and rule rows are seeded from `backend/seed/catalog.json` by an idempotent loader that upserts by slug (D007). Plan counts are derived: placed = placements for that crop, and remaining = max(0, quantity − placed). A count above the quantity displays as, for example, `3 / 2`; nothing is corrected automatically.

### Placement semantics

- Creating a placement or planting without a window uses the crop's default window for that year.
- Creating a placement through the API defaults to `source=manual` and `locked=true`.
- Removing a crop from the plan also removes its placements.
- A completed plan is read-only until it is reopened. `POST /plans/{id}/complete` replaces the plantings previously created from that plan with one planting per placement. Reopening leaves the history untouched.
- Editing any placement moves it to `source=manual`. The user can toggle `locked`.
- `generate-layout` may delete or replace **only** placements that are both `source=suggested` and `locked=false`. Everything else is fixed input (D008).
- Timing overlap: two placements in the same bed conflict if their month ranges share more than a boundary month. Handover in the same month is allowed, for example lettuce Apr–Jun followed by beans Jun–Sep. The API still accepts conflicting placements and reports them as `timing_conflict`. The generator never creates one (D009).

### Scoring (pure module `backend/services/layout/`)

Inputs are plain dataclasses: beds with adjacency, history, rules, fixed placements, and requested demand. There is no database access, so a solver can replace the module behind the same interface later.

Per candidate (crop, bed, month window), a normalized score from 0 to 100 combines:

- **Rotation:** years since the same crop was last grown in that bed, compared with the crop rule. A missing rule falls back to the family rule, then to a default of 3 years.
- **Family rotation:** the same check against any crop of the same family.
- **Neighbours:** companion rules against crops in adjacent beds whose seasons overlap. Beds count as adjacent when their edge distance is at most 1.0 m (a configurable constant).
- **Timing:** whether the crop's default window fits the free time in the bed. Occupancy includes history plantings and the placements of the previous and next years' plans, so garlic planted for next year reserves this autumn.

Bands:

| Score | Band |
| --- | --- |
| ≥ 80 | `very_suitable` |
| ≥ 60 | `suitable` |
| ≥ 40 | `possible` |
| lower | `some_considerations` |

`no_free_season` is the only "impossible" state. It is shown in neutral grey, not red.

Reason codes are stable strings that the mobile app maps to short labels: `good_rotation_interval`, `same_crop_recent`, `same_family_recent`, `compatible_neighbor`, `less_compatible_neighbor`, `fits_season`, `limited_season`, `timing_conflict`, `no_history`.

### Auto-layout

1. Build slots from free month windows in active beds, after subtracting fixed placements.
2. Greedy pass: place the most constrained demand first, meaning the fewest good slots.
3. Local improvement: pairwise swap and move passes over suggested placements. Stop when nothing improves or when a time budget of about 1 s is reached.
4. The total objective is the sum of scores. Ties are broken by stable IDs, so identical input gives identical output.

Demand that cannot be placed is returned as `unplaced: [{crop_id, count, reason}]` with HTTP 200, not as an error. The endpoint replaces the replaceable placements and returns the new placements in one transaction.

### API additions beyond the requirements minimum

- `DELETE /gardens/{id}`, `POST /beds/{id}/restore`, `GET /gardens/{id}?include_archived=true`
- `GET /plans?garden_id=`, `DELETE /plans/{id}`, `POST /plans/{id}/complete`, `POST /plans/{id}/reopen`
- `POST /plans/{id}/crops` upserts by `crop_id`; `DELETE /plans/{id}/crops/{crop_id}` removes it
- `GET /gardens/{id}/plantings?year_from=&year_to=` (garden-wide history view)
- `GET /plans/{id}/suitability?crop_id=` returns per-bed `{bed_id, score, band, reasons}` for colour-coding.
- `POST /plans/{id}/evaluate` recomputes scores for all placements after manual edits. It is also run implicitly by the placement write endpoints.

All private routes are authenticated and garden-owner scoped. They return 404 for foreign records.

### Mobile (`mobile/`, D005)

- Stack: Expo SDK (latest stable), Expo Router with a tab layout (Garden, Plan, History, Settings), TanStack Query, and Zustand for the editor's selection and mode.
- UI libraries: `react-native-svg` for the bed canvas; `react-native-gesture-handler` and `reanimated` for pan, zoom, drag, and resize; `@gorhom/bottom-sheet`; `expo-secure-store` for the token.
- API types are generated from FastAPI's OpenAPI schema with `openapi-typescript` (D010).
- Interaction model (D011):
  - Tapping is the complete path: select a crop in the plan tray, see the beds colour-coded, then tap a bed to place it. Drag is an accelerator on top.
  - Move and resize use drag handles, with a numeric edit fallback in the bed sheet.
  - Snap to a 0.1 m grid.
- Layout is tablet-first. Wide screens show the canvas and a side panel; narrow screens show the canvas and a bottom sheet. Portrait and landscape are both supported, and touch targets are at least 48 dp.

## Phases and acceptance checks

### Phase 0 — Project initialization (done)

- [x] Requirements stored; PROJECT, STATUS, and DECISIONS initialized; this plan drafted.

### Phase 1 — Backend domain and CRUD (complete, pending review)

- [x] Removed the items, example and jobs features along with their tests. Renamed the app (settings, README, web shell). Token lifetime now defaults to 30 days.
- [x] Added models and the migration `0003_crop_domain`. It drops `items`, `background_jobs` and the `jobstatus` enum; the downgrade recreates the empty tables and drops the new enums. Trimmed the Vite frontend to sign-in plus a gardens page, and moved the smoke test to the garden, history and plan API.
- [x] Seed catalogue: 43 crops across 9 families with en/fi names, 15 rotation rules and 29 companion pairs. Added a validating, idempotent loader and `make seed`; the smoke stack seeds on start.
- [x] CRUD routes from requirements §9 plus the additions above, including plan completion and reopening. Covered by ownership, validation, overlap-acceptance and completion tests.
- [x] Checks: see validation results.

### Phase 2 — Scoring and auto-layout

- [ ] Build the pure `layout` module with unit tests covering rotation gaps, the family fallback, adjacency, the timing boundary, and determinism.
- [ ] Add the `generate-layout`, `suitability`, and `evaluate` endpoints.
- [ ] Checks:
  - Locked and manual placements are never changed.
  - Unplaceable demand is reported.
  - A 50-bed and 30-crop fixture completes in under 2 s.

### Phase 3 — Mobile foundation

- [ ] Scaffold the Expo app: lint and Prettier, generated API client, sign-in with secure-store persistence, and the tab shell.
- [ ] Gardens list and create; the garden canvas with add, move, resize, rename, and archive for beds.
- [ ] The bed sheet with a seasonal timeline, plus history add, edit, and delete; the History tab by garden and by bed.

### Phase 4 — Planning flow

- [ ] Plan tab: create or select a plan by year; the crop picker with search and quantity; placed/requested counts.
- [ ] Select a crop to see suitability colours with a legend and reasons, then tap a bed to place it (locked). Also support moving and unplacing, and toggling the lock.
- [ ] **Fill remaining** shows a progress state, then the result. Unplaced crops appear as a gentle notice.

### Phase 5 — Hardening and handoff

- [ ] Retire the Vite `frontend/` and move CI and `make smoke` to the Expo web export plus Playwright against the real stack.
- [ ] Test on at least one Android device or emulator and one iOS device or simulator (Expo Go or a development build). Record which ones.
- [ ] Walk through all 12 success criteria end to end. Update ARCHITECTURE, DEVELOPMENT, and the root README.

## Questions and decisions

Answered on 2026-09-28 (see [PROJECT.md](../PROJECT.md#product-answers-2026-09-28)): hosting stays open but scalable (D013), Finnish and English (D014), completing a plan writes history, and cross-year crops reserve the bed (D012). Still open: the hosting provider and distribution channel (Phase 5). For device testing on WSL2, use `npx expo start --tunnel` or WSL mirrored networking.

## Validation results

| Check / command | Result | Commit or relevant context |
| --- | --- | --- |
| Phase 0 docs: local link check and `git diff --check` | Pass (0 broken links) | Documentation only |
| `ruff check .`, `ruff format --check .` | Pass | Phase 1 working tree |
| `pytest` | 64 passed on Python 3.12 and 3.14 | SQLite; includes the migration chain 0001→0003, downgrade to base, and seed idempotence. The first CI run failed on a migration annotation that only Python 3.14 skips evaluating; it is fixed, and 3.12 now runs locally too. |
| PostgreSQL migration checks | Pass: `upgrade 0002`, `upgrade head`, `alembic check` (no changes), seed ×2 (second run adds nothing), cascade and `SET NULL` behaviour, `downgrade base`, `upgrade head`, `alembic check` | Embedded **PostgreSQL 16** via `pgserver` in an isolated uv environment (no Docker or local server available). CI runs PostgreSQL 18. |
| Frontend `lint`, `format:check`, `build`, `npm test` | Pass; 10 browser tests (desktop and mobile) | Mocked API |
| Smoke spec against a real stack | Pass | Embedded PostgreSQL 16, migrated and seeded, with uvicorn and the Vite proxy. **Not** run through Nginx/Docker: `make smoke` needs Docker, which this WSL distro lacks. CI runs it. |

## Handoff / completion

- Implemented: Phases 0–1. The backend domain, catalogue, CRUD and plan completion are on `feat/phase1-backend-domain`.
- Remaining work or blockers: Phases 2–5. `make smoke` and the PostgreSQL 18 checks have not run locally for lack of Docker; confirm them in CI after pushing.
- Next concrete step: push the branch and open a PR so that CI covers Docker smoke and PostgreSQL 18. Then start Phase 2 with the pure `layout` module (scoring inputs as dataclasses, occupancy including neighbouring years' plans) and its unit tests.
- Deviations from the plan:
  - The garden canvas size was dropped; it is derived from the beds.
  - Several plans per garden and year were replaced by one per garden and year (D012).
  - `POST /plans/{id}/crops` upserts, and `DELETE /plans/{id}/crops/{crop_id}` is keyed by crop.
  - Completed plans are read-only until reopened.
