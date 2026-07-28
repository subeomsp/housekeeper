# Voice Inventory — Flutter App

Flutter frontend for the Voice Inventory Agent. It talks to the FastAPI backend
over HTTP; it never touches the database directly.

Phase 2 Flutter 기본 앱과 Phase 3 Action Plan 확인·편집 화면까지 구현됐다. 전체
프로젝트 상태와 다음 Phase 계획은 `../HANDOFF.md` (§19~20)를 먼저 확인한다.

## Requirements

- Flutter 3.32.8+ (Dart 3.8+)
- macOS + Xcode/CocoaPods (for the `-d macos` desktop target used in development)

## Run

```bash
cd frontend
flutter pub get
flutter run -d macos
```

A native macOS window opens for desktop development. The final target is
Android (Phase 5).

The completed basic app supports inventory list/detail and controls, manual
stock-in/out, target quantity changes, event correction/cancellation, item
creation/edit/archive/restore, refresh, common error states, and a text-first
Action Plan generation/confirmation/edit/delete flow before real voice processing.

From Home, `텍스트로 음성 흐름 테스트` submits a temporary Transcript, generates a Plan,
and opens `/action-plan/:requestId`. The screen shows the original Transcript, warnings,
confidence, and every Action. An Action can be changed to stock-in, stock-out, or target quantity
using an active inventory item and its official unit, or deleted when at least one other Action
remains. The execute button is intentionally disabled until the approval/transaction slice is
implemented.

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
