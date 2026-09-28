# CropCycle

A mobile-first crop rotation planner. Gardeners draw their beds, record what grew where, list next season's crops, place the ones they care about, and let the app suggest the rest. The backend is FastAPI with PostgreSQL. Python 3.12+ dependencies use uv; the web frontend uses Node 24 and npm. The Expo mobile app is planned in [plan 002](md/plans/002-crop-rotation-mvp.md).

Implemented so far:

- Registration and login by email or username, with Argon2 password hashing and expiring JWTs (30 days by default for mobile sign-in).
- A shared crop catalogue with 43 crops, families, rotation rules and companion rules. Names are in English and Finnish, loaded from versioned seed data.
- Owner-scoped gardens with rectangular beds (archived rather than deleted), planting history, and yearly plans with requested crops, locked manual placements, and completion into history.
- Year-month planting windows that can cross the new year, for example garlic from October to July.
- Rate limits on registration, login and writes; liveness and readiness endpoints; configurable CORS; automated tests.
- A minimal web frontend (sign-in and gardens) kept until the Expo app replaces it.

- Rotation, family, neighbour and timing scoring with gentle suitability bands and reason codes; **Fill remaining** optimizes the whole plan around locked choices.

## Development context

The [md/](md/README.md) folder contains the project context, implemented architecture, development workflow, current status, decisions, and an implementation-plan template. Start there when adapting this repository to a new project or handing work between developers and AI agents. Root [AGENTS.md](AGENTS.md) directs coding agents to that context and explains what to keep updated.

## Local development

Use Linux, macOS, or WSL with GNU Make, [uv](https://docs.astral.sh/uv/getting-started/installation/), and Node 24/npm installed. From the repository root:

```bash
make setup
```

This installs locked Python/frontend dependencies and creates `.env` with a generated secret if it does not exist. Existing `.env` files are preserved. Set `DATABASE_URL` to a **dedicated, empty database** in your PostgreSQL instance (for example, in `~/code/devstack`). PostgreSQL extensions and Redis are not required. Normal development does not start another database server.

```bash
make migrate
make seed
make dev
```

`make dev` checks the settings, database migration revision, and ports, then starts both servers. Ctrl+C or either server exiting stops both. It points Vite at the local backend even if `frontend/.env.local` specifies a different proxy; use the separate commands below when working with a remote API. It never applies migrations automatically. `make seed` loads or updates the crop catalogue; it is safe to repeat.

Open <http://localhost:5173> for the UI and <http://127.0.0.1:8000/docs> for the API. Registration requires a password of 12–128 characters and a username of 3–100 letters, digits, dots, underscores, or hyphens. Login uses form fields `username` and `password`; `username` can contain either the username or email.

If another project uses the default ports, run `make dev BACKEND_PORT=18000 FRONTEND_PORT=15173`; the proxy follows the backend port. To run servers separately, use `make backend` and `make frontend` in separate terminals. All commands are listed by `make help`:

| Command | Purpose |
| --- | --- |
| `make setup` | Install locked dependencies and safely initialize `.env` |
| `make dev` | Start and stop both local servers together |
| `make migrate` | Apply migrations to the configured database |
| `make seed` | Load or update the crop catalogue (idempotent) |
| `make check` | Backend checks plus frontend lint, formatting, build, and mocked browser tests |
| `make check-backend` / `make check-frontend` | Run checks for one side |
| `make smoke` | Test the real full stack in disposable Docker containers |

Without Make, the underlying commands are:

```bash
uv sync --all-packages --locked
uv run --no-sync python -m scripts.setup_env
npm --prefix frontend ci
# Configure DATABASE_URL in .env before migrating:
uv run --no-sync alembic -c backend/alembic.ini upgrade head
uv run --no-sync python -m backend.seed
uv run --no-sync python -m scripts.dev
```

To install only backend dependencies, use `uv sync --package backend`. Vite forwards `/api/*` requests to the backend on port 8000, so no CORS change is needed. The web UI includes registration/login, a protected account page, and a minimal gardens page. Tokens stay in memory; reloading the page signs you out. See [frontend/README.md](frontend/README.md) for configuration, structure, and browser tests.

## Configuration

The backend reads the repository-root `.env` regardless of the working directory. Environment variables override it. See [.env.example](.env.example) for the full configuration.

| Setting | Default / requirement |
| --- | --- |
| `DATABASE_URL` | Required; `postgresql+psycopg://user:password@host:5432/database` |
| `SECRET_KEY` | Required; random secret of at least 32 bytes |
| `DEBUG` | `false` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `43200` (30 days) |
| `CORS_ORIGINS` | Empty; explicit comma-separated URLs or a JSON array |

JWT signing uses HS256. Keep `.env` out of Git. Existing `postgresql://` URLs are normalized to use psycopg 3. URL-encode special characters in database credentials.

## Docker

The backend installs from `uv.lock`; the frontend builds from `frontend/package-lock.json` and is served by unprivileged Nginx. Compose runs the backend; the UI is an optional profile. Application data lives in PostgreSQL.

Set `.env`'s `DATABASE_URL` to an address reachable **from the container**. For a host-published devstack database, use `host.docker.internal` instead of `localhost` (the host-gateway mapping is included). Ensure that PostgreSQL's published port is reachable from that Docker network. Alternatively, attach the backend to your devstack network and use its database service hostname.

```bash
docker compose build
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
docker compose run --rm backend python -m backend.seed
docker compose up -d
# Include the React frontend on port 5173:
docker compose --profile ui up --build -d
```

Migrations and seeding are explicit deployment steps. Run them once before starting new application processes. The image does not enable hot reload.

## API

Interactive documentation is at `/docs`, and [tests/test.http](tests/test.http) has request examples. Every route except registration, login and health requires a bearer token. Private records are scoped to the signed-in user's gardens; missing and foreign records both return 404.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register`, `/auth/login` | Create a user (201); issue a bearer token |
| GET | `/auth/me` | Current user |
| GET | `/crops`, `/crop-families`, `/rotation-rules`, `/companion-rules` | Shared catalogue (read-only) |
| GET, POST | `/gardens` | List or create gardens |
| GET, PUT, DELETE | `/gardens/{id}` | Garden with active beds (`?include_archived=true` for all); rename; delete everything in it |
| POST | `/gardens/{id}/beds` | Add a bed (`name`, `x`, `y`, `width`, `height` in metres) |
| PUT, DELETE | `/beds/{id}` | Replace geometry and name; archive (history is kept) |
| POST | `/beds/{id}/restore` | Un-archive a bed |
| GET, POST | `/beds/{id}/plantings` | Bed history; record a planting |
| GET | `/gardens/{id}/plantings` | Garden history, optionally `year_from` / `year_to` |
| PUT, DELETE | `/plantings/{id}` | Edit or remove a history entry |
| GET, POST | `/plans` | List a garden's plans (`?garden_id=`); create one plan per garden and year (409 if it exists) |
| GET, PUT, DELETE | `/plans/{id}` | Plan with requested crops, placed counts, and placements with their current `assessment`; rename; delete (its history stays) |
| POST | `/plans/{id}/complete`, `/plans/{id}/reopen` | Write placements to history and lock the plan; allow edits again |
| POST | `/plans/{id}/crops` | Request a crop, or change its quantity |
| DELETE | `/plans/{id}/crops/{crop_id}` | Remove a requested crop and its placements |
| POST | `/plans/{id}/placements` | Place a crop in a bed (manual and locked by default) |
| POST | `/plans/{id}/generate-layout` | **Fill remaining**: replace unlocked suggestions with a new layout; returns the plan and `unplaced` crops |
| GET | `/plans/{id}/suitability?crop_id=` | Score, band and reasons for placing the crop in each active bed |
| PUT, DELETE | `/plan-placements/{id}` | Move, re-time, lock or unlock; remove |
| GET | `/health`, `/ready` | Process liveness; database connectivity (503 on failure) |

Planting windows use `start_month` and `end_month` as `"YYYY-MM"` strings, covering at most 24 months. If they are omitted, the crop's default window for the given year is used. A planting's `year` must lie within its window, and a placement's window must include part of its plan's year. Only malformed input is rejected. Rotation and overlap concerns are guidance and never block a write ([D009](md/DECISIONS.md)). Completed plans are read-only (409) until reopened. Assessments use the bands `very_suitable`, `suitable`, `possible`, `some_considerations` and `no_free_season` (timing clash only), with reason codes that clients translate. Rate limits use process-local memory; configure shared storage before deploying multiple workers. The included Nginx proxy limits request bodies to 1 MiB.

## Project layout

```text
backend/
  api/endpoints/    HTTP routes and dependencies
  core/            Settings, database sessions, rate limiting
  models/          ORM models and request/response schemas
  services/        Authentication, gardens/history, plans, catalogue, planting windows
  seed/            Crop catalogue data (catalog.json) and its idempotent loader
  alembic/         Schema migrations
  main.py          App factory and health endpoints
frontend/src/      React pages, routing, session state, and API client
frontend/tests/    Desktop and mobile browser tests
frontend/e2e/      Real full-stack smoke test and browser runner image
scripts/           Setup, development server, and smoke-test helpers
tests/             Isolated automated tests and REST client examples
```

Domain errors raised by services (`services/errors.py`) are mapped to 404/409/422 responses in `create_app()`. Add models in `backend/models/database.py`, request/response schemas in `schemas.py`, business logic in `services/`, and routers in `api/endpoints/`. Register new routers in `create_app()`.

```bash
uv run --no-sync alembic -c backend/alembic.ini revision --autogenerate -m "describe change"
uv run --no-sync alembic -c backend/alembic.ini upgrade head
```

Review generated migrations before applying them.

**Migration history:** `0003_crop_domain` drops the template's example `items` and `background_jobs` tables without keeping their data; downgrading recreates them empty. Earlier revisions come from the template. `0001_core` replaced a pre-cleanup history and must not be stamped over such an installation.

## Checks

```bash
uv sync --all-packages --locked
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
```

Backend tests use isolated SQLite databases, with no running API or external services. They cover ownership, validation, catalogue seeding, plan completion, and migrations. CI also checks migration upgrade, schema consistency, and downgrade on PostgreSQL. The frontend has separate build, lint, and browser checks:

```bash
cd frontend
npm ci
npm run lint
npm run build
npx playwright install chromium
npm test
```

### Full-stack smoke test

Run `make smoke` from the root with Docker Engine and Compose v2 available. It builds the production backend/frontend plus a browser runner, starts a separate PostgreSQL 18 database, applies migrations, and seeds the catalogue, and tests registration, login, persistence across reload, the garden/history/plan API, and cross-user isolation through Nginx. There are no mocked API calls.

The standalone [compose.smoke.yaml](compose.smoke.yaml) publishes no host ports, reads no `.env`, and uses a unique Compose project per run. Database files live in container tmpfs. The script removes its containers, network, and volumes on success, failure, or interruption. It does not use or stop your development stack. Docker build cache/images are retained for later runs. Run one smoke command at a time per checkout because the artifact directory is shared.

Browser failure traces/screenshots and container logs are saved under `frontend/test-results/smoke/` (ignored by Git). CI runs the same Make target and uploads that directory on failure. No host Python, npm, or browser installation is required for this target. The test runner installs Chromium matching the locked Playwright dependency inside its image.

### Dependency maintenance

[Dependabot configuration](.github/dependabot.yml) schedules weekly updates for the uv workspace, frontend npm packages, GitHub Actions, Dockerfiles, and Compose images. Minor/patch version updates are grouped per ecosystem; major versions remain separate PRs. Python/npm security updates have separate groups when security updates are enabled in the repository settings. No updates are merged automatically.

Review dependency PRs and their CI results, especially framework, runtime, and database major versions. The smoke check rebuilds the images and uses the browser version from the lockfile. Update the documented runtime requirements when accepting runtime-version changes. See [GitHub's configuration reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) for the grouping options.

Authentication follows the libraries used in [FastAPI's security guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/); container dependency installation follows [uv's Docker guide](https://docs.astral.sh/uv/guides/integration/docker/).
