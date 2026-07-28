# Voice Inventory Agent Backend

FastAPI backend for the Voice Inventory Agent.

For the current implementation status, product decisions, and remaining work, see
`../HANDOFF.md` before continuing development.

Phase 1 inventory APIs are complete and deployed. Phase 3 is now in progress: the Voice Request,
Action Plan, and Item Alias persistence foundation is implemented, together with a temporary text
Transcript entry API. Action Plan generation is available through a provider-neutral Planner
interface with an OpenAI Responses API adapter and strict Structured Output validation. Review,
editing, approval, and execution are intentionally separate follow-up slices. Mutations still follow
the Phase 1 Event/Snapshot transaction rules, and neither text entry nor Plan generation changes
inventory.

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
POST   /api/v1/voice-requests/text
POST   /api/v1/voice-requests/{request_id}/action-plan
GET    /api/v1/action-plan/{request_id}
PATCH  /api/v1/action-plan/{request_id}/actions/{action_id}
DELETE /api/v1/action-plan/{request_id}/actions/{action_id}
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

The temporary text Voice Request endpoint accepts a non-blank `transcript`, associates it with the
current Household, and returns a request identifier with status `planning`. It stores only the
Voice Request in one transaction: it does not create an Action Plan, Inventory Event, Snapshot
change, or Audit Log. This lets the Action Plan workflow be developed before audio upload and STT.

Action Plan generation loads that Voice Request and the Household's active items, calls the
configured Planner outside a database transaction, then re-reads current inventory and validates
the structured result before saving it. A successful Plan and the Voice Request transition to
`waiting_confirmation` are committed together. Repeating the same request returns the existing Plan
without another Provider call. Provider and validation failures leave no Plan and mark the Voice
Request `failed` so it can be retried.

The server only accepts Plan version `1.0`, `stock_in`/`stock_out`, positive quantities with at most
three decimal places, explicit confirmation, unique Action IDs, and valid active Household item
references. It rechecks official names, default units, duplicate Actions, confidence rules, and
negative inventory in Action order. Unit conversion rules are not yet persisted: a different raw
unit must remain unresolved and require user input, while an AI-applied conversion is rejected.
New or unmatched items also require user input.

The Action Plan read/edit endpoints power the Flutter confirmation screen. Edits accept an active
item ID, `stock_in`/`stock_out`/`set_quantity`, a quantity, and the item's exact default unit. They
lock the Voice Request and Action Plan in that order, rebuild the selected Action from current
official item data, validate the complete Plan against current Snapshots, and save only
`payload_json` in one transaction. User-confirmed Actions receive confidence `1.0`, no AI warnings,
and `requires_user_input: false`. `set_quantity` permits zero; stock changes remain strictly
positive. The last Action cannot be deleted because an Action Plan must remain non-empty.

Plan edits and deletions never create Inventory Events or update Inventory Snapshots. The Plan
summary becomes a neutral confirmed-action count after an edit so an AI-generated quantity summary
cannot become stale. Approval and execution remain a separate Phase 3 slice.

Set `OPENAI_API_KEY` outside source control to enable the OpenAI adapter. `LLM_PROVIDER` defaults to
`openai`, and `OPENAI_MODEL` defaults to `gpt-5.6-sol` but can be overridden. Without a key the
generation endpoint returns `503 PLANNER_NOT_CONFIGURED`; the rest of the application remains
available.

The current Alembic head is `20260728_0003`. It adds `voice_requests`, `action_plans`, and
`item_aliases`. A Voice Request belongs to one Household, has an optional transcript/audio path for
future audio states, and can have at most one Action Plan. Item Alias uniqueness is scoped to a
Household by normalized alias.

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
4. To enable Action Plan generation, set `OPENAI_API_KEY` as a Render secret. Optionally override
   `OPENAI_MODEL`; never commit the key to `.env` or source control.
5. The container runs `alembic upgrade head` on start, then serves `uvicorn app.main:app`. Render polls
   `/ready` (which checks the database) before routing traffic.

The development seed (`app.scripts.seed`) is not run automatically; run it manually only against a
development database if you want sample data.
