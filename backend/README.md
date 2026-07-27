# Voice Inventory Agent Backend

FastAPI backend for the Voice Inventory Agent.

For the current implementation status, product decisions, and remaining work, see
`../HANDOFF.md` before continuing development.

The project is implementing Phase 1 from `../product_spec.md`. The application bootstrap, health
check, PostgreSQL async session infrastructure, Alembic environment, Phase 1 database models, and
initial migration are implemented. The idempotent development seed is also available. Inventory
Item creation, list, update, archive, and restore APIs are implemented. Current inventory list, item
detail, manual Inventory Event creation, setting the current quantity, Inventory Event history, and
event correction and cancellation are available, along with an internal Snapshot rebuild service. The
remaining Phase 1 work is real PostgreSQL integration tests and the deployment close-out (Dockerfile,
readiness check, Neon migration/seed). Mutations write Audit Logs in the same transaction; Item Alias
matching remains a Phase 3 feature.

## Requirements

- Python 3.12 or newer
- `uv`

## Setup

```bash
uv sync
cp .env.example .env
```

Set `DATABASE_URL` in `.env` to a PostgreSQL URL. A regular `postgresql://` URL is normalized to the
SQLAlchemy `postgresql+asyncpg://` driver automatically.

For Neon, retain the TLS query parameter:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:password@host/database?ssl=require
```

Do not use a production database for tests.

## Migration

The Alembic async environment is ready. After migrations are added, apply them with:

```bash
uv run alembic upgrade head
```

## Seed

After applying the migration, create the Phase 1 development household, user, membership, five
inventory items, and zero-quantity snapshots:

```bash
uv run python -m app.scripts.seed
```

The seed uses stable identifiers and checks existing records, so running it repeatedly does not
create duplicates.

## Run

```bash
uv run uvicorn app.main:app --reload
```

Check the server:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Implemented API endpoints:

```text
POST /api/v1/inventory-items
GET  /api/v1/inventory-items
PATCH  /api/v1/inventory-items/{item_id}
DELETE /api/v1/inventory-items/{item_id}
POST   /api/v1/inventory-items/{item_id}/restore
GET    /api/v1/inventory
GET    /api/v1/inventory/{item_id}
PUT    /api/v1/inventory/{item_id}/quantity
POST   /api/v1/inventory-events
GET    /api/v1/inventory-events
PATCH  /api/v1/inventory-events/{event_id}
DELETE /api/v1/inventory-events/{event_id}
```

Item creation normalizes the item name, rejects Household-level duplicates, and creates its
zero-quantity Inventory Snapshot in the same transaction.

Item archive is a soft delete and requires a zero Inventory quantity. Changing the default unit
also requires zero quantity. These mutations lock the item and Snapshot before validation.

Item creation, metadata update, archive, and restore write before/after state to `audit_logs`.
Renamed item values are not automatically treated as voice aliases.

The current inventory list reads Snapshot quantities and supports search, category, zero-quantity
filtering, sorting, and pagination. Item detail combines the Snapshot with the ten most recent
Inventory Events.

Manual Inventory Event creation accepts only `stock_in` and `stock_out` from clients; it locks the
Snapshot, computes signed quantity on the backend, rejects negative inventory, and commits the
Event, Snapshot update, and Audit Log together. `adjustment_in/out`, `initial_stock`, and
`event_reversal` are backend-internal and rejected on external requests.

Setting the current quantity (`PUT /api/v1/inventory/{item_id}/quantity`) takes the desired final
quantity, not a delta. It locks the Snapshot, computes `target - current`, records the difference as
an `adjustment_in`/`adjustment_out` Event, and updates the Snapshot and Audit Log in the same
transaction. When the target equals the current quantity it writes nothing and returns
`changed: false` with a null `event_id`.

The Inventory Event history (`GET /api/v1/inventory-events`) is a read-only, household-scoped ledger
query with `item_id`, `event_type`, `source`, `from`, `to`, `limit`, and `offset` filters, ordered by
`created_at` descending. The `event_type` filter accepts backend-internal and reversal types so the
full history can be inspected.

Correcting (`PATCH /api/v1/inventory-events/{event_id}`) and cancelling
(`DELETE /api/v1/inventory-events/{event_id}`) an event never mutate the original row. Both lock the
original event and the Snapshot, create an `event_reversal` with the opposite signed quantity, stamp
`reversed_at`/`reversed_by`/`reversal_event_id` on the original, and update the Snapshot in one
transaction; correction additionally writes a `correction`-sourced replacement event. A result that
would drive the Snapshot negative is rejected, and already-reversed or reversal events cannot be
corrected or cancelled.

`InventoryService.rebuild_inventory_snapshot(household_id, item_id)` is an internal recovery/testing
helper (not an HTTP endpoint). It locks the Snapshot and recomputes it from the sum of every event's
signed quantity, including originals and their reversals, so a reversed original and its reversal
cancel out. Reversed originals are never excluded from the sum.

## Verify

```bash
uv run pytest
uv run ruff check .
uv run mypy app tests
```

Unit tests run without a database. Integration tests under `tests/integration/` need a real
PostgreSQL database and are skipped unless `TEST_DATABASE_URL` is set (use a dedicated Neon `test`
branch, never the runtime database). The harness drops and recreates the schema for each test, so the
target database must be disposable.

## Deploy

The backend deploys as a Docker image via `backend/Dockerfile`. The image is built on the platform
(Render), so no local Docker is required. `render.yaml` at the repository root is a Render Blueprint:
Docker runtime, `dockerContext: ./backend`, and `healthCheckPath: /ready`.

Deployment checklist:

1. Push the repository to GitHub (Render deploys from Git).
2. In Render, create a Blueprint (or Web Service) from the repo; `render.yaml` supplies the build and
   health-check configuration.
3. Set `DATABASE_URL` in the Render dashboard as a secret. Use a Neon branch **separate from the test
   branch** (e.g. `production`). Use `?ssl=require`; the app normalizes Neon connection strings
   (drops `channel_binding`, maps `sslmode`) automatically.
4. The container runs `alembic upgrade head` on start, then serves `uvicorn app.main:app`. Render polls
   `/ready` (which checks the database) before routing traffic.

The development seed (`app.scripts.seed`) is not run automatically; run it manually only against a
development database if you want sample data.
