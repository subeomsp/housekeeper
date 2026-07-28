# Voice Inventory — Flutter App (Phase 2)

Flutter frontend for the Voice Inventory Agent. It talks to the FastAPI backend
over HTTP; it never touches the database directly.

For overall project status and the Phase 2 plan, read `../HANDOFF.md` (§19) first.

## Requirements

- Flutter 3.32.8+ (Dart 3.8+)
- macOS + Xcode/CocoaPods (for the `-d macos` desktop target used in development)

## Run

```bash
cd frontend
flutter pub get
flutter run -d macos
```

A native macOS window opens — that is the app during Phase 2 development. The
final target is Android (Phase 5).

Current Phase 2 screens support inventory list/detail, manual stock-in/out,
target quantity changes, event history with correction/cancellation, and item
creation/edit/archive/restore. Cross-screen error and list-control finishing
work follows next; see `../HANDOFF.md` §19.4.

### API server

The app points at the deployed Render backend by default:

```
https://housekeeper-vo2q.onrender.com   (see lib/core/config/app_config.dart)
```

No `.env` is needed to run the frontend. To point at a different backend:

```bash
flutter run -d macos --dart-define=API_BASE_URL=https://your-host
```

> Use the macOS desktop target, not Chrome/web: the backend has no CORS
> middleware, so a browser would block calls to Render. Desktop apps have no
> CORS restriction. The macOS `network.client` entitlement is already set.

### If the inventory is empty / writes fail with DATABASE_ERROR

The backend has no auth (Phase 1) and uses a fixed dev Household/User UUID whose
rows are created by the backend seed. A fresh database must be seeded once:

```bash
cd ../backend
# backend/.env must have DATABASE_URL pointing at the target Neon branch
uv run alembic upgrade head
uv run python -m app.scripts.seed   # idempotent
```

The current Render/Neon branch is already migrated + seeded with demo data, so
reusing it needs no extra step.

## Verify

```bash
flutter analyze   # keep at 0 issues
flutter test
```

## Structure

Feature-first (`core/` + `features/`) with Riverpod (state), go_router (nav),
and dio (HTTP). See `../HANDOFF.md` §19.3 for the full tree and conventions.
