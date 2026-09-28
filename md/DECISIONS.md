# Architecture and development decisions

Record choices that future maintainers would otherwise have to rediscover: boundaries, ownership rules, important dependencies, or operational tradeoffs. Routine edits belong in Git history. Proposed decisions are not permission to implement them.

## D001 — Keep the starter domain-neutral

- Status: superseded by D007 once plan 002 Phase 1 lands (items are replaced by the crop domain).
- Decision: demonstrate private CRUD with a small item containing a title and description. Keep file processing and product-specific models out of the baseline.
- Reason: copied projects need an ownership example without inheriting an upload workflow or a particular product domain.
- Consequence: a new project should rename or replace items. Shared catalogs and user-owned collections can be separate models rather than forcing all data into items.

## D002 — Use in-memory browser sessions in the baseline

- Status: superseded by D006 for the mobile client.
- Decision: hold the bearer token in React state and clear the session on an authenticated 401.
- Reason: demonstrate authentication without adding persistent browser token storage or a refresh-token subsystem to the starter.
- Consequence: page reload signs the user out. A product that needs persistent login must design that flow explicitly; local sign-out alone does not revoke tokens.

## D003 — Keep the background example in-process

- Status: superseded by D008 (the jobs example is removed in plan 002; layout generation is synchronous).
- Decision: demonstrate a short FastAPI background task with a stored job record and a separate database session.
- Reason: show task submission and status lookup without requiring queue infrastructure in every copied project.
- Consequence: task execution is not durable. Long-running analysis or ingestion that needs retries and recovery requires a separate worker design.

## D004 — Isolate full-stack tests from development data

- Status: accepted.
- Date: 2026-09-27.
- Decision: run the same `make smoke` target locally and in CI, with production app images and a separate Compose file, network, and temporary PostgreSQL data.
- Reason: exercise the actual proxy, API contract, and persistence without relying on or mutating a developer's database. No host ports or local `.env` are used.
- Consequences: smoke tests require Docker and build a browser runner; initial runs are slower than mocked UI tests. Browser installation follows the locked Playwright version rather than a separately versioned browser image. Normal application migrations remain explicit.
- Reference: [finalization plan](plans/001-template-finalization.md).

## D005 — Expo mobile app replaces the Vite web frontend

- Status: accepted.
- Date: 2026-09-28.
- Context: the requirements specify React Native, Expo, and TypeScript for iOS and Android. Development happens on WSL2, where running emulators is awkward.
- Decision: build a single Expo app in `mobile/` with Expo Router, TanStack Query, and Zustand. Use its web target (`expo export --platform web`) for fast UI iteration and for Playwright tests in CI. Retire `frontend/` in plan 002 Phase 5, after the web-target smoke test replaces it.
- Alternatives: keep a separate web app, which would duplicate the UI; bare React Native without Expo, which is harder to build on WSL2.
- Consequences: some native gestures behave differently on web, so a manual device check is required before release (Phase 5).

## D006 — Persistent device sign-in with the existing token auth

- Status: accepted.
- Date: 2026-09-28.
- Decision: keep the template's username/password and JWT authentication. Store the access token in `expo-secure-store`, and make its lifetime configurable with a 30-day default for the mobile client. Refresh tokens and revocation are deferred.
- Reason: the success criteria require reopening a saved plan on the device. This is the smallest change that achieves that with tested code.
- Consequences: a stolen token is valid until it expires. Revisit with refresh and revocation before a public release.

## D007 — Shared agronomic catalogue as versioned seed data

- Status: accepted.
- Date: 2026-09-28.
- Decision: store crop families, crops, rotation rules, and companion rules as global, read-only tables. Load them from `backend/seed/catalog.json` with an idempotent upsert keyed by stable `slug`s (`make seed`). User data (gardens and everything below them) is owned through `garden.user_id`.
- Reason: the requirements say rules must live in data, not in client code. Slugs make updates safe across environments without depending on database IDs.
- Alternatives: Alembic data migrations, which are harder to revise; per-user catalogues, which are deferred but possible later through a nullable owner column.
- Consequences: removing a catalogue entry that history references needs an explicit deprecation flag rather than a delete.

## D008 — Isolated, deterministic layout engine with a narrow replace rule

- Status: accepted.
- Date: 2026-09-28.
- Decision: implement scoring and auto-layout as a pure Python module (`backend/services/layout/`) that works on dataclasses with no database access. It uses a greedy placement pass with the most constrained demand first, followed by swap/move local improvement under a time budget, and stable tie-breaking. `generate-layout` runs synchronously and may replace only placements that are `source=suggested` and `locked=false`.
- Reason: this meets "optimize the whole plan" and "never change manual or locked choices" without OR-Tools. The pure interface allows a constraint solver to be swapped in later. Deterministic output keeps behaviour predictable for users and tests.
- Consequences: results are good rather than optimal. Large gardens are bounded by the time budget.

## D009 — Guidance, not enforcement

- Status: accepted.
- Date: 2026-09-28.
- Decision: the API rejects only structurally invalid input, such as an out-of-range month, `start > end`, a non-positive size, or foreign ownership. Rotation, companion, and timing concerns never cause a rejection. They are exposed as a score, one of four bands, and reason codes. Overlapping full-bed placements are accepted and flagged `timing_conflict`, and the generator never creates them. A same-month handover between sequential crops is not an overlap.
- Reason: this follows the requirements' core principle, and history months are approximate.

## D010 — Generate mobile API types from OpenAPI

- Status: accepted.
- Date: 2026-09-28.
- Decision: generate TypeScript types for the mobile app from FastAPI's OpenAPI schema with `openapi-typescript`, a development dependency. A check fails when the generated file is stale.
- Reason: the template mirrors types by hand, which drifts as the domain API grows.

## D011 — Tap-first editing, drag as an accelerator

- Status: accepted.
- Date: 2026-09-28.
- Decision: every editing action can be completed by tapping: select a crop, then tap a bed; select a bed, then use the sheet or handles. Dragging to place or move is layered on top. Bed geometry snaps to 0.1 m. Beds are archived rather than hard-deleted, so rotation history survives accidental deletion.
- Reason: drag and drop is unreliable across tablets, phones, web, and accessibility tools. The requirements ask for tap alternatives anyway.

## D012 — Year-month planting windows that can cross the new year

- Status: accepted.
- Date: 2026-09-28.
- Context: autumn-planted crops such as garlic occupy a bed from October to the following July, and the user wants that reservation respected. The requirements' `year` plus month-number fields cannot express it.
- Decision:
  - Plantings and placements store `start_month` and `end_month` as dates, always the first day of the month. The API exchanges them as `"YYYY-MM"` strings.
  - A planting's `year` is its season year and must fall within its window. A placement's window must overlap its plan's year.
  - Crops define default windows with `default_start_month`, `default_end_month`, and `default_start_year_offset` (-1 for "planted the previous autumn"). When `end < start`, the window ends in the following year.
  - There is one plan per garden and year, so neighbouring years' plans can be treated as fixed occupancy.
  - Month handover (A ends in June, B starts in June) is not an overlap.
- Alternatives: month numbers 1–12 with a wrap flag, which is ambiguous about which year owns the crop; or absolute month indices, which are unreadable in the API.
- Consequences: sub-month precision is not modelled. Perennial crops that stay in place for several years are out of scope.

## D013 — Portable single-service backend that is ready for more users

- Status: accepted.
- Date: 2026-09-28.
- Decision: keep the backend a stateless container configured only by environment, with PostgreSQL as the sole state. Migrations and seeding are explicit deployment steps. All user data is owner-scoped from the start. No hosting provider is chosen yet.
- Consequences: running multiple API workers requires shared rate-limit storage (see the template limits in ARCHITECTURE). Self-registration may need to be closable when hosting publicly.

## D014 — Finnish and English from the start

- Status: accepted.
- Date: 2026-09-28.
- Decision: store catalogue display names as `names: {"en": ..., "fi": ...}` JSON; both are required in the seed file. The API returns all names, and the client chooses by the user's locale and falls back to English. Mobile UI strings live in per-locale message files, and reason codes are translated client-side.
- Alternatives: separate translation tables, which are heavier than two locales need but can be migrated to later.

## Adding a decision

Copy this outline, assign the next ID, and link it from a related plan when useful:

```markdown
## D00N — Short decision title

- Status: proposed | accepted | superseded by D00N
- Date: YYYY-MM-DD
- Context: the problem and relevant constraints.
- Decision: the choice and why it fits.
- Alternatives: meaningful options considered, if any.
- Consequences: costs, limitations, and follow-up work.
- References: related plan, code, issue, or PR.
```

When a choice changes, mark the old entry superseded and link the replacement. When copying the template, review whether these baseline decisions still apply.
