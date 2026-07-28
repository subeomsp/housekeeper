# Voice Inventory Agent 인수인계 문서

작성일: 2026-07-21 (최종 갱신: 2026-07-28)  
현재 단계: Phase 1 Backend 완료·배포됨. **Phase 2 (Flutter 앱) 진행 중** — 2-1(골격+재고목록), 2-2(품목상세), 2-3(입고/소비·목표수량) 완료, 다음은 2-4(기록 목록·Event 정정/취소). 상세는 아래 §19.

## 1. 가장 먼저 읽을 문서

1. `AGENTS.md`
   - 작업 범위, 불변 규칙, 사용자 보고 형식이 정의되어 있다.
2. `product_spec.md`
   - 프로젝트의 Source of Truth이다.
   - 현재 구현 기준은 특히 63번부터 75번까지이다.
3. 이 문서 `HANDOFF.md`
   - 실제 구현 상태와 대화 중 확정된 제품 결정을 정리한다.

문서와 코드가 충돌하면 `product_spec.md`를 우선하되, 임의로 결정을 바꾸지 말고 사용자에게 제품 흐름을 설명한 후 확인한다.

## 2. 사용자와 협업할 때 중요한 점

사용자는 코드를 직접 읽지 않고 제품 흐름을 검토하려고 한다.

응답은 다음 표식으로 시작한다.

```text
━━━━━━━━━━━━━━━━━━━━

🤖 Assistant

━━━━━━━━━━━━━━━━━━━━
```

API 작업 완료 보고에는 파일 목록만 나열하지 말고 API마다 다음 내용을 설명한다.

- 어떤 화면과 사용자 행동에 사용되는가
- 무엇을 입력받고 무엇을 반환하는가
- Backend 내부에서 어떤 순서로 검증·조회·저장하는가
- Transaction과 Row Lock의 범위는 어디인가
- 어떤 조건에서 거부되고 Front에는 어떤 오류가 전달되는가
- 기본값과 제한 등 제품 검토가 필요한 결정은 무엇인가
- 다음 API와 어떻게 이어지는가

사용자는 이 설명을 보고 잘못된 제품 결정을 지적하고 수정하는 방식으로 협업한다.

## 3. 프로젝트 핵심 원칙

- 음성은 기본 CRUD를 없애는 기능이 아니라 재고 변경 입력을 빠르게 만드는 기능이다.
- 앱에서는 품목 생성·조회·수정·보관·복원과 재고 수동 관리가 가능해야 한다.
- 재고 수량의 원본은 `InventoryEvent`이다.
- `Inventory`는 Front에 현재 수량을 빠르게 제공하는 Snapshot이다.
- Event와 Snapshot 변경은 항상 같은 Transaction에서 수행한다.
- Event 생성 전 Snapshot Row를 Lock한다.
- `signed_quantity`는 Backend가 계산하며 클라이언트가 전달하지 않는다.
- 음수 재고는 허용하지 않는다.
- 기존 Event는 물리 수정하거나 삭제하지 않는다.
- 잘못된 Event는 Reversal과 필요 시 대체 Event로 정정한다.
- 품목 삭제는 물리 삭제가 아닌 `is_active=false` Soft Delete이다.
- LLM은 DB를 수정하지 않고 Execution Plan만 만든다.
- 사용자 승인 전에는 음성 Action을 실행하지 않는다.

## 4. 대화 중 확정된 주요 제품 결정

### 4.1 기본 CRUD와 음성의 관계

음성은 재고 변경 Event 생성을 편하게 하는 핵심 기능이지만, 앱의 기본 관리 기능을 대체하지 않는다.

```text
앱 수동 관리
→ 품목 CRUD
→ 현재 수량 직접 설정
→ 수동 입고·소비
→ Event 정정·취소

음성 관리
→ 자연어를 Action Plan으로 변환
→ 사용자 확인
→ 같은 Backend Service를 통해 실행
```

### 4.2 Event와 Snapshot

```text
InventoryEvent
→ 통장 거래내역
→ +5, -2, +1

Inventory Snapshot
→ 현재 잔액
→ 4
```

목록 화면은 Snapshot을 읽고, 기록 화면은 Event를 읽는다. Snapshot이 잘못되면 모든 Event를 다시 합산해 재구축한다.

### 4.3 수동 입력의 두 가지 의미

수동 입력을 하나로 취급하지 않는다.

```text
수동 입고·소비
→ 변경량 입력
→ stock_in / stock_out

현재 수량 수정
→ 최종 목표 수량 입력
→ Backend가 현재 값과 차이를 계산
→ adjustment_in / adjustment_out
```

예를 들어 현재 5개일 때:

```text
수동 소비 2개
→ 최종 3개

현재 수량을 2개로 설정
→ adjustment_out 3
→ 최종 2개
```

Backend와 Flutter 앱 모두 변경량을 받는 수동 Event 흐름과 목표 수량 설정 흐름을 제공한다.

### 4.4 현재 이름, 이름 변경 이력, 음성 Alias

세 개를 분리한다.

```text
inventory_items.name
→ 현재 화면에 표시할 공식 이름

audit_logs
→ 품목명·단위·카테고리·활성 상태 변경 이력

item_aliases
→ 사용자가 같은 품목을 다르게 말하는 음성 표현
```

예:

```text
현재 이름: 펩시제로라임
Alias: 제로콜라, 펩시제로, 라임콜라
```

품목명을 수정해도 이전 이름을 Alias로 자동 등록하지 않는다. Alias는 사용자가 음성 표현을 특정 품목과 연결하고 저장을 승인했을 때 Phase 3에서 생성한다.

이름 변경은 Audit Log에만 기록하며 음성 매칭에는 사용하지 않는다.

### 4.5 음성으로 미등록 품목 입력

가능하지만 조용히 자동 생성하지 않는다.

```text
“아몬드브리즈 두 개 사 왔어”
→ 기존 품목 검색 실패
→ 신규 품목 후보 Action 표시
→ 이름·단위 확인
→ 사용자 승인
→ 품목 + Snapshot + 입고 Event를 같은 Transaction에서 생성
```

미등록 품목의 `stock_out`은 수량 0에서 음수 재고가 되므로 바로 실행하지 않고 기존 품목 선택 또는 현재 수량 입력을 요구하는 방향이 권장되었다.

### 4.6 Action Plan 음성 명령과 호출어

- Action Plan 화면에서 `승인`, `취소`, `수량 3개로 수정` 같은 음성 명령은 v1.1 TODO이다.
- 앱이 닫힌 상태에서 자체 호출어를 항상 듣는 기능은 Android 백그라운드 마이크·배터리·개인정보 제약이 크므로 v2.0 연구 항목이다.
- MVP에서는 상시 음성 대기를 구현하지 않는다.

## 5. 현재 기술 구성

- Python 3.12+
- `uv`
- FastAPI
- SQLAlchemy 2.x Async
- `asyncpg`
- Alembic Async Migration
- Pydantic Settings
- pytest / pytest-asyncio / httpx
- Ruff
- mypy strict

Backend 경로는 `backend/`이다.

계층 책임:

```text
API
→ 요청 검증, 의존성 확인, 응답 변환

Service
→ 비즈니스 검증, Transaction orchestration, 계산

Repository
→ SQLAlchemy 조회·저장·Row Lock

Model
→ PostgreSQL 영속성 구조

Schema
→ 외부 API 계약
```

## 6. 환경설정과 DB 기반

구현 파일:

- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/api/dependencies.py`
- `backend/alembic.ini`
- `backend/migrations/env.py`
- `backend/.env.example`

특징:

- 일반 `postgresql://` URL을 `postgresql+asyncpg://`로 정규화한다.
- Neon URL은 나중에 `.env`의 `DATABASE_URL`에 넣으면 된다.
- Async Engine과 Session Factory가 분리되어 있다.
- API는 `DatabaseSession` 의존성으로 Session을 주입받는다.
- Phase 1은 인증이 없으므로 고정 개발용 Household/User UUID를 사용한다.

로컬 `backend/.env`에 `TEST_DATABASE_URL`(별도 Neon `test` 브랜치)을 설정했고 통합 테스트로 실제 접속을 검증했다. 앱 런타임용 `DATABASE_URL`(운영/개발 DB)과 Migration·Seed 실제 적용은 아직 검증하지 않았다.

## 7. 구현된 DB 모델과 Migration

### 7.1 모델

```text
Household
User
HouseholdMember
InventoryItem
Inventory
InventoryEvent
AuditLog
```

주요 관계:

```text
Household
├── HouseholdMember ── User
├── InventoryItem
│   ├── Inventory Snapshot
│   └── InventoryEvent
└── AuditLog
```

SQLAlchemy `relationship()`은 아직 추가하지 않았고 외래키와 명시적 Join을 사용한다.

### 7.2 Migration

```text
20260720_0001_initial_schema.py
→ households
→ users
→ household_members
→ inventory_items
→ inventory
→ inventory_events

20260720_0002_add_audit_logs.py
→ audit_logs
```

Alembic 현재 Head는 `20260720_0002`이다.

Offline SQL 생성은 성공했지만 실제 PostgreSQL에 적용한 적은 없다.

## 8. 개발용 Seed

실행 명령:

```bash
uv run python -m app.scripts.seed
```

생성 대상:

```text
Household: 우리 집
User: 테스트 사용자
Membership: owner

우유 / 개 / drink
계란 / 개 / food
제로콜라 / 캔 / drink
맥주 / 캔 / drink
참치캔 / 개 / food
```

각 품목에는 수량 0 Snapshot을 만든다. 고정 UUID와 기존 Row 검사를 사용해 반복 실행 시 중복되지 않도록 작성했다.

`seed_database(session_factory)`는 팩토리를 인자로 받아 테스트 엔진으로도 실행할 수 있다. 실제 Neon 테스트 DB에서 2회 실행 후 중복이 없음을 통합 테스트로 검증했다(`test_migration_and_seed.py`).

## 9. 구현된 API와 제품 흐름

### 9.1 Health

```http
GET /health
```

응답:

```json
{"status":"ok"}
```

`/health`는 애플리케이션 프로세스만 확인하는 Liveness probe이다(DB 미확인).

DB 연결까지 확인하는 Readiness probe를 추가했다.

```http
GET /ready
```

`SELECT 1`이 성공하면 `200 {"status":"ready","database":"ok"}`, DB에 못 붙으면 `503 {"status":"not_ready","database":"error"}`를 반환한다. Render 등 로드밸런서가 백엔드가 실제로 요청을 처리할 수 있을 때만 트래픽을 보내도록 하는 용도이다.

### 9.2 품목 생성

```http
POST /api/v1/inventory-items
```

사용처:

```text
재고 화면
→ 품목 직접 추가
→ 이름·기본 단위·카테고리 입력
```

내부 흐름:

```text
입력 검증
→ 품목명 정규화
→ Household 내 중복 확인
→ InventoryItem 생성
→ 수량 0 Snapshot 생성
→ Audit Log 생성
→ 같은 Transaction에서 Commit
```

새 품목은 초기 수량을 받지 않고 항상 0으로 생성한다. 초기 수량은 목표 수량 설정 API로 Event를 만들어 입력할 예정이다.

### 9.3 품목 목록

```http
GET /api/v1/inventory-items
```

지원 조건:

```text
search
category
include_inactive=false
limit=50
offset=0
```

품목 관리용 목록이며 수량 0 품목도 포함한다. 현재 기본 정렬은 이름 오름차순이다.

### 9.4 품목 수정

```http
PATCH /api/v1/inventory-items/{item_id}
```

수정 가능 항목:

```text
name
default_unit
category
```

흐름:

```text
품목과 Snapshot Lock
→ Household 확인
→ 이름 중복 확인
→ 기본 단위 변경 시 현재 수량 0 확인
→ 품목 변경
→ before/after Audit Log
→ Commit
```

카테고리에 `null`을 전달하면 카테고리를 제거한다. 보관된 품목 정보도 수정할 수 있다.

### 9.5 품목 보관·복원

```http
DELETE /api/v1/inventory-items/{item_id}
POST /api/v1/inventory-items/{item_id}/restore
```

보관은 물리 삭제가 아니다.

```text
현재 수량 0 확인
→ is_active=false
→ Audit Log
```

수량이 남아 있으면 `409 ITEM_HAS_INVENTORY`로 거부한다. 보관과 복원은 최종 상태 기준으로 멱등하게 동작한다.

### 9.6 현재 재고 목록

```http
GET /api/v1/inventory
```

사용처:

```text
메인 재고 화면
→ 활성 품목의 현재 수량 표시
```

지원 조건:

```text
search
category
include_zero=true
sort=updated_at | name | quantity
order=asc | desc
limit=50
offset=0
```

Snapshot을 읽으므로 Event 전체를 합산하지 않는다. 보관 품목은 제외한다. `updated_at`은 품목 메타데이터 수정 시각이 아니라 Snapshot 수량 변경 시각이다.

### 9.7 품목 상세

```http
GET /api/v1/inventory/{item_id}
```

응답 구성:

```text
현재 품목 정보
현재 Snapshot 수량
최근 InventoryEvent 10개
```

Event는 생성 시각 내림차순으로 반환한다. 보관 품목도 직접 URL로 조회할 수 있다. 전체 Event Pagination은 Event 목록 API(9.10)에서 제공한다.

### 9.8 수동 Inventory Event 생성

```http
POST /api/v1/inventory-events
```

사용처:

```text
품목 상세
→ 입고 또는 소비 선택
→ 변경량 입력
```

입력 예:

```json
{
  "item_id": "uuid",
  "event_type": "stock_in",
  "quantity": 2,
  "unit": "개",
  "note": "장보기"
}
```

내부 흐름:

```text
Transaction 시작
→ 품목과 Snapshot Row Lock
→ 품목·Household·활성 상태 확인
→ 요청 단위와 기본 단위 비교
→ Backend에서 signed_quantity 계산
→ 음수 재고 검증
→ InventoryEvent 생성
→ Snapshot 갱신
→ Audit Log 생성
→ Commit
```

응답에는 `previous_quantity`와 `current_quantity`가 함께 들어간다.

현재 요청 Schema는 다음 Type만 허용한다.

```text
stock_in
stock_out
```

`adjustment_in`, `adjustment_out`, `initial_stock`, `event_reversal`은 Backend 내부 전용이며 클라이언트 요청을 거부한다(`422 VALIDATION_ERROR`). `adjustment_in/out`은 목표 수량 설정 API가 생성한다.

### 9.9 현재 수량 설정

```http
PUT /api/v1/inventory/{item_id}/quantity
```

사용처:

```text
재고 화면
→ 실제 남은 수량 직접 입력
→ 최종 목표 수량 저장
```

입력 예:

```json
{
  "quantity": 2,
  "unit": "개",
  "note": "실제 수량 확인"
}
```

`quantity`는 증감량이 아니라 최종 목표 수량이다. Snapshot을 직접 덮어쓰지 않고 현재 수량과의 차이를 Adjustment Event로 기록한다.

내부 흐름:

```text
Transaction 시작
→ 품목과 Snapshot Row Lock
→ 품목·Household·활성 상태·단위 확인
→ delta = target - current 계산
→ delta > 0 이면 adjustment_in
→ delta < 0 이면 adjustment_out
→ delta = 0 이면 Event·Snapshot·Audit를 만들지 않음
→ InventoryEvent + Snapshot + Audit Log 저장
→ Commit
```

응답:

```json
{
  "event_id": "uuid 또는 null",
  "item_id": "uuid",
  "previous_quantity": 5,
  "current_quantity": 2,
  "changed": true,
  "created_at": "2026-07-20T10:00:00Z 또는 null"
}
```

목표 수량이 현재 수량과 같으면 `changed=false`, `event_id=null`, `created_at=null`을 반환하고 아무 것도 저장하지 않는다. 목표 수량 Schema는 `quantity >= 0`을 강제하므로 음수 재고가 될 수 없다.

### 9.10 Inventory Event 목록

```http
GET /api/v1/inventory-events
```

사용처:

```text
기록 화면
→ 재고 변경 내역(통장 거래내역) 조회
→ 품목·유형·기간별 필터
```

지원 필터:

```text
item_id
event_type   (stock_in/out, adjustment_in/out, initial_stock, event_reversal)
source       (manual, voice, system, correction)
from         (created_at >= )
to           (created_at <= )
limit=50
offset=0
```

Household로 항상 범위를 제한하는 조회 전용 API이므로 Row Lock이나 Snapshot 합산을 하지 않는다. `event_type`은 내부 전용·Reversal 유형까지 이력 필터로 허용한다(생성 제한과는 별개). 정렬은 `created_at` 내림차순, 동일 시각은 `id` 내림차순이다. 응답은 `{ items, total }`이며 각 항목에 `id, item_id, event_type, quantity, signed_quantity, unit, source, note, created_by, created_at`이 들어간다. 다른 Household의 `item_id`를 지정하면 빈 목록을 반환한다.

### 9.11 Event 정정

```http
PATCH /api/v1/inventory-events/{event_id}
```

사용처:

```text
기록 화면
→ 잘못 입력한 Event 정정
→ 예: 우유 +20 을 +2 로 수정
```

입력 예:

```json
{
  "event_type": "stock_in",
  "quantity": 2,
  "unit": "개",
  "note": "20개가 아니라 2개"
}
```

원본 Event를 물리 수정하지 않는다. 같은 Transaction에서 `event_reversal`(원본 반대값)과 대체 Event를 만들고 원본에 `reversed_at`·`reversed_by`·`reversal_event_id`를 기록한다.

내부 흐름:

```text
Transaction 시작
→ 원본 Event Row Lock
→ Household·정정 가능 상태(취소되지 않음, Reversal 아님) 확인
→ 대상 품목 Snapshot Row Lock
→ 대체 Event 단위 검증
→ 최종 수량 = 현재 - 원본 signed + 대체 signed
→ 최종 수량이 음수면 전체 거부
→ event_reversal 저장
→ 대체 Event 저장(source=correction)
→ 원본에 reversed 정보 기록
→ Snapshot 갱신
→ Audit Log(inventory_event_corrected)
→ Commit
```

응답: `{ original_event_id, reversal_event_id, replacement_event_id, previous_quantity, current_quantity, corrected_at }`. 대체 Event의 `event_type`은 수동 생성과 동일하게 `stock_in`/`stock_out`만 허용한다.

### 9.12 Event 취소

```http
DELETE /api/v1/inventory-events/{event_id}
```

대체 Event 없이 `event_reversal`만 만드는 점을 제외하면 정정과 동일한 흐름이다. 최종 수량 = 현재 - 원본 signed 이며 음수가 되면 거부한다. Audit는 `inventory_event_reversed`로 남긴다.

응답: `{ original_event_id, reversal_event_id, previous_quantity, current_quantity, cancelled_at }`.

이미 취소된 Event와 `event_reversal` Event는 정정·취소할 수 없다(`409 EVENT_ALREADY_REVERSED` / `409 EVENT_NOT_CORRECTABLE`). Snapshot 재구축 시 취소된 원본을 합계에서 제외하면 Reversal과 이중 차감되므로 원본은 항상 합산에 포함한다.

## 10. 공통 오류 형식

```json
{
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "현재 재고보다 많은 수량을 소비할 수 없습니다.",
    "details": {
      "item_id": "uuid",
      "current_quantity": "2",
      "requested_quantity": "3"
    }
  }
}
```

현재 주요 오류:

```text
VALIDATION_ERROR
ITEM_NOT_FOUND
DUPLICATE_ITEM_NAME
HOUSEHOLD_ACCESS_DENIED
ITEM_HAS_INVENTORY
UNIT_CHANGE_REQUIRES_ZERO_INVENTORY
UNIT_MISMATCH
INACTIVE_ITEM
INSUFFICIENT_INVENTORY
EVENT_NOT_FOUND
EVENT_ALREADY_REVERSED
EVENT_NOT_CORRECTABLE
DATABASE_ERROR
```

## 11. Audit Log 현재 동작

같은 Transaction에서 다음 Action을 기록한다.

```text
inventory_item_created
inventory_item_updated
inventory_item_archived
inventory_item_restored
inventory_event_created
inventory_event_corrected
inventory_event_reversed
```

품목 변경은 `before_json`과 `after_json`을 저장한다. 실제 값이 변하지 않은 멱등 요청은 Audit Log를 만들지 않는다.

현재 Audit Log 조회 API와 Front 관리 기록 화면은 없다.

## 12. 현재 검증 상태

2026-07-21 실행 결과:

```text
pytest: 79 passed, 11 skipped   (TEST_DATABASE_URL 미설정 시)
pytest: 90 passed               (TEST_DATABASE_URL 설정 시, 실제 Neon 연결)
ruff: 통과
mypy strict: 통과
Alembic head: 20260720_0002
```

통합 테스트 11건(`tests/integration/`)은 `TEST_DATABASE_URL`이 없으면 skip, 있으면 실제 PostgreSQL에 붙어 실행된다. 스모크 2건 + 시나리오 7건 + Migration/Seed 2건.

통합 테스트가 잡은 실제 결함(수정 완료):

- **FK 삽입 순서 버그(공통 원인).** 이 프로젝트는 `relationship()` 없이 FK 컬럼만 쓰는데, SQLAlchemy ORM의 flush 순서는 주로 relationship 기반이라 relationship이 없으면 여러 테이블 insert 순서가 FK를 보장하지 못한다. 그래서 부모 행을 먼저 `flush()`해야 한다.
  - `InventoryItemRepository.add_with_snapshot`: item을 먼저 flush한 뒤 snapshot을 flush하도록 수정.
  - `app/scripts/seed.py`: household·user를 먼저 flush(그 뒤 membership·item), item을 flush한 뒤 snapshot을 추가하도록 수정.
  - Fake 기반 유닛 테스트로는 드러나지 않던 버그로, 실제 Neon 연결 통합 테스트가 잡았다.

Neon 연결 관련 실무 메모:

- Neon이 주는 연결 문자열의 `channel_binding`은 제거하고 `sslmode`는 `ssl`로 바꿔야 asyncpg가 붙는다. 이 정리는 `Settings.normalize_database_url`이 자동 수행하므로 URL을 거의 그대로 넣어도 된다.
- 통합 테스트 fixture는 매 테스트마다 `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`으로 초기화한다(FK 순서·잔여 테이블에 영향받지 않음). Neon Pooler와의 호환을 위해 asyncpg `statement_cache_size=0`을 쓴다. 대상 DB는 반드시 버려도 되는 테스트 전용이어야 한다.

주의:

- 현재 로직 검증은 전부 Unit Test이다(Fake Repository/Fake Transaction, Service Mock).
- 실제 PostgreSQL Transaction, FK, Row Lock, Rollback, 동시성은 아직 검증하지 않았다.
- `tests/integration/` 골격(`conftest.py`의 `db_session` fixture + 스모크 테스트)은 추가했으나, 시나리오 테스트(우선순위 5 목록)는 아직 작성하지 않았다.
- `TEST_DATABASE_URL`(별도 Neon 테스트 브랜치)이 설정되면 통합 테스트가 실제 PostgreSQL에 붙어 실행되고, 없으면 skip된다.
- 실제 Neon 연결·Migration 적용·Seed 실행은 아직 검증하지 않았다.

검증 명령:

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
uv run mypy app tests
uv run alembic heads
uv run alembic upgrade head --sql
```

## 13. 아직 결정이 필요한 제품 검토 지점

### 13.1 수동 Event API가 허용할 Event Type (결정 완료)

`2026-07-21` 결정: 외부 수동 Event POST는 `stock_in`, `stock_out`만 허용한다.

```text
일반 UI 노출
→ stock_in
→ stock_out

Backend 내부 전용
→ adjustment_in
→ adjustment_out
→ initial_stock
→ event_reversal
```

`InventoryEventCreate.event_type`을 `ManualEventType = Literal["stock_in", "stock_out"]`으로 제한했다. 그 외 Type은 `422 VALIDATION_ERROR`로 거부한다. `adjustment_in/out`은 목표 수량 설정 API(9.9)가 생성한다.

### 13.2 수동 Event Idempotency (결정 완료: 이연)

`2026-07-21` 결정: 수동 입력 API(Event 생성, 목표 수량 설정)에 Idempotency Key는 지금 적용하지 않는다.

같은 POST를 두 번 보내면 여전히 Event가 두 번 생성된다. Idempotency는 Action Plan Execute를 구현할 때 통합 설계한다.

### 13.3 과거 Event의 품목명 표시

InventoryEvent는 `item_id`만 저장한다. 품목명을 변경하면 과거 Event도 화면에서 현재 공식 이름으로 표시된다.

이름 변경 이력은 Audit Log에 남지만, Event 당시 이름을 보존하지는 않는다. 현재 합의는 이 구조를 유지하는 것이다.

### 13.4 상세 화면 최근 Event 수

현재 고정 10개이다. 전체 기록은 Event 목록 API(9.10)에서 Pagination으로 조회한다.

## 14. 다음 구현 순서

### 우선순위 1: 현재 수량 설정 API (완료, 2026-07-21)

```http
PUT /api/v1/inventory/{item_id}/quantity
```

구현 완료. 상세는 9.9를 참고한다. `quantity`는 최종 목표 수량이며 Snapshot을 직접 덮어쓰지 않고 현재 수량과의 차이를 `adjustment_in/out` Event로 기록한다. delta가 0이면 아무 것도 저장하지 않고 `changed=false`로 반환한다. Unit Test(서비스 7건, API 3건)를 추가했다.

### 우선순위 2: Inventory Event 목록 API (완료, 2026-07-21)

```http
GET /api/v1/inventory-events
```

구현 완료. 상세는 9.10을 참고한다. 필터는 `item_id, event_type, source, from, to, limit, offset`이며 조회 전용이다. Unit Test(서비스 1건, API 2건)를 추가했다.

### 우선순위 3: Event 정정·취소 (완료, 2026-07-21)

```http
PATCH  /api/v1/inventory-events/{event_id}
DELETE /api/v1/inventory-events/{event_id}
```

구현 완료. 상세는 9.11·9.12를 참고한다. 정정은 `event_reversal` + 대체 Event, 취소는 `event_reversal`만 만들고 최종 수량이 음수면 전체 거부한다. 이미 취소된 Event와 Reversal Event는 다시 정정·취소할 수 없다. Unit Test(서비스 8건, API 3건)를 추가했다.

### 우선순위 4: Snapshot 재구축 Service (완료, 2026-07-21)

외부 API로 노출하지 않는 관리·복구·테스트용 Service 함수
`InventoryService.rebuild_inventory_snapshot(session, *, household_id, item_id)`로 구현했다.

```text
Snapshot Row Lock
→ 품목·Household 확인
→ 원본 Event와 Reversal Event를 모두 포함해 signed_quantity 합산
→ 합계가 현재 Snapshot과 다르면 Snapshot을 합계로 복구(같으면 변경 없음)
→ Commit
```

취소된 원본을 합계에서 제외하면 Reversal과 이중 차감되므로 절대 제외하지 않는다. Unit Test 4건(드리프트 복구, 일치 시 무변경, 미존재, 타 Household)을 추가했다.

### 우선순위 5: 실제 PostgreSQL Integration Test (완료, 2026-07-21)

`tests/integration/`에 실제 Neon 테스트 브랜치로 도는 통합 테스트를 작성했다. `conftest.py`가 `TEST_DATABASE_URL`로 Async Engine을 만들고 테스트마다 스키마를 리셋하는 `db_session`/`integration_engine` fixture를 제공한다. URL 미설정 시 전체 skip.

시나리오(`test_inventory_flow.py`, 7건):

- 품목 생성과 Snapshot 생성 Transaction ✓
- 중복 품목 409(실제 Unique 제약) ✓
- Event와 Snapshot 원자적 Commit ✓
- 음수 재고 요청 후 DB 상태 불변(예외 시 전체 Rollback) ✓
- `SELECT ... FOR UPDATE` 동시성(동시 stock_out 2건 → 정확히 1건만 성공, 초과판매 방지) ✓
- 다른 Household 접근 403 ✓
- Event 정정 후 원장·Snapshot 정합성 + Snapshot 재구축 = Event 합계 일치 ✓

Migration/Seed(`test_migration_and_seed.py`, 2건):

- 빈 DB에 실제 alembic `upgrade head`(0001→0002) 적용 → `alembic_version`=head, 7개 테이블 생성 검증 ✓ (서브프로세스로 alembic 실행, `DATABASE_URL`을 테스트 URL로 주입)
- Seed 2회 실행 후 중복 없음(멱등성): 1회차 생성 수 = 5 items/5 snapshots, 2회차 = 0, 최종 household 1·user 1·item 5·snapshot 5 ✓

남은 선택 항목(원자성은 음수 재고 Rollback 테스트로 이미 입증됨):

- Snapshot 저장 실패 주입 / 정정 중간 실패 시 전체 Rollback 같은 장애 주입 테스트는 필요 시 추가.

운영 Neon DB를 테스트에 사용하지 않는다. 별도 Neon `test` 브랜치를 사용한다.

### 우선순위 6: Phase 1 마감 작업 (완료, 2026-07-28)

- `/ready` DB 확인 API ✓ (상세는 9.1)
- `backend/Dockerfile` + `backend/.dockerignore` ✓ (uv 기반, CMD가 `alembic upgrade head` 후 uvicorn 실행. 빌드는 Render에서, 로컬 Docker 불필요. `.env`는 이미지 제외)
- `render.yaml` ✓ (저장소 루트, Docker runtime 참고용. 실제 배포는 Blueprint 유료라 Web Service 수동 설정으로 진행)
- 실제 운영 Neon 브랜치 연결 + Migration 자동 적용 ✓ (컨테이너 기동 시 `alembic upgrade head`)
- README 배포 섹션 ✓
- **Render 배포 완료** ✓ (2026-07-28, Docker Web Service 수동 설정, `/ready` → 200 OK 확인)

실제 배포 방식(확정): Render **Web Service 수동 설정**(Blueprint는 유료).
- Root Directory = `backend`, Dockerfile Path = `Dockerfile`, Runtime = Docker, Branch = `main`.
- 환경변수: `DATABASE_URL`(test와 분리된 Neon 운영 브랜치, `?ssl=require`), `APP_ENV=production`.
- Health Check Path = `/ready`. 컨테이너 기동 시 `alembic upgrade head` 자동 실행.
- Seed는 자동 실행하지 않음(필요 시 개발 DB에만 수동).
- Free 플랜은 15분 무요청 시 슬립 → 첫 요청 콜드스타트 있음.

배포 결정: 백엔드는 Render(Docker 이미지 빌드는 Render 서버에서 수행, 로컬 Docker 불필요), DB는 Neon 운영 브랜치. Vercel은 서버리스라 이 상시 실행 ASGI 백엔드에는 부적합하며 추후 Flutter 프론트 배포용으로만 고려.

Phase 1 완료 전에는 Flutter, STT, LLM, Action Plan, Android Widget을 시작하지 않는다.

## 15. 현재 없는 주요 기능

```text
Audit Log 조회 API
Item Alias 모델과 검색
```

Flutter, Android Widget, 음성, STT, LLM, Action Plan은 Phase 1 범위 밖이라 전혀 구현하지 않았다.

## 16. 바로 확인할 주요 파일

```text
AGENTS.md
product_spec.md
backend/README.md
backend/pyproject.toml

backend/app/main.py
backend/app/core/config.py
backend/app/core/database.py
backend/app/core/exceptions.py
backend/app/core/exception_handlers.py

backend/app/api/v1/inventory_items.py
backend/app/api/v1/inventory.py
backend/app/api/v1/inventory_events.py

backend/app/services/inventory_item_service.py
backend/app/services/inventory_service.py

backend/app/repositories/inventory_item_repository.py
backend/app/repositories/inventory_repository.py
backend/app/repositories/inventory_event_repository.py
backend/app/repositories/audit_log_repository.py

backend/migrations/versions/20260720_0001_initial_schema.py
backend/migrations/versions/20260720_0002_add_audit_logs.py
```

## 17. 저장소 상태 관련 주의

- Git 저장소이며 원격은 `github.com/subeomsp/housekeeper` (`main` 브랜치). 초기 히스토리는 단일 커밋으로 정리됨.
- `__pycache__`, `.venv`, pytest/mypy/ruff 캐시는 `.gitignore` 대상이다.
- `backend/.env`에 `DATABASE_URL`/`TEST_DATABASE_URL` Secret이 있으며 `.gitignore` 대상이다. 절대 커밋하지 않는다(현재 추적되는 것은 `.env.example`뿐).
- 운영 `DATABASE_URL`은 코드/깃이 아니라 Render 대시보드 환경변수에만 둔다.

## 18. Claude가 바로 이어서 작업할 때 권장 시작 지시

```text
AGENTS.md와 HANDOFF.md를 먼저 완전히 읽고 product_spec.md 63~75번을 구현 기준으로 사용한다.

현재 Phase 1 Backend 구현을 이어간다.

우선순위 1~5(현재 수량 설정 API, 수동 Event Type 제한, Event 목록 API,
Event 정정·취소, Snapshot 재구축 Service, 실제 PostgreSQL Integration Test)는
2026-07-21에 구현 완료했다. 실제 Neon `test` 브랜치로 통합 테스트(11건)가 돈다.
Idempotency는 Action Plan Execute 단계로 이연하기로 결정했다.

통합 테스트가 실제 FK 삽입 순서 버그 2건(`add_with_snapshot`, `seed`)을 잡아 수정했다.

남은 일은 우선순위 6(Phase 1 마감)뿐이다:
Dockerfile, `/ready` Readiness API(DB 확인), 실제 Neon(운영/개발 DB)로 Migration·Seed 적용,
Render 실행 설정, README 최종 동기화. 앱 런타임 `DATABASE_URL`은 아직 검증하지 않았다(통합 테스트는 `TEST_DATABASE_URL`만 사용).

API 완료 보고는 코드를 읽지 않는 사용자가 제품 흐름을 검토할 수 있도록 사용처, 입력·출력, 내부 처리 순서, 실패 조건, 검토할 결정을 설명한다.
```

## 19. Phase 2 (Flutter 앱) 진행 상황과 이어서 작업하는 법

Phase 1 백엔드는 완료·배포되었고, 지금은 **Phase 2 Flutter 앱**을 구현 중이다.
이 절만 읽으면 다른 컴퓨터에서 `git clone` 후 그대로 이어서 작업할 수 있다.

### 19.1 배포/환경 사실 (그대로 사용)

- Backend API(운영/개발): `https://housekeeper-vo2q.onrender.com` (Render Web Service, Docker, 수동 설정).
  - 헬스체크 `GET /ready` → `{"status":"ready","database":"ok"}`.
  - API prefix `/api/v1`. 인증 없음(Phase 1 설계, 고정 dev Household/User UUID).
- DB: Neon 운영 브랜치. **Render 대시보드의 `DATABASE_URL` 시크릿**으로만 연결(레포에 없음).
- 로컬 `backend/.env`(gitignore)에 `DATABASE_URL`=이 운영 브랜치, `TEST_DATABASE_URL`=test 브랜치가 들어있다. **다른 노트북에서는 이 `.env`를 새로 만들어야 한다**(값은 Neon 대시보드/Render 시크릿에서 복사). 프론트만 돌릴 거면 `.env` 불필요(아래 참고).
- **중요(무인증 설계상 필수 셋업)**: 새 빈 DB는 `alembic upgrade head` 뒤 **반드시 seed 1회** 실행해야 고정 dev Household/User가 생겨 쓰기 API가 동작한다. 안 하면 품목/이벤트 생성이 `DATABASE_ERROR`(FK 위반)로 막힌다. 현재 운영 Neon 브랜치는 이미 seed 완료 + 데모 데이터(우유/맥주/제로콜라/계란/참치캔) 입고까지 되어 있으므로, **같은 브랜치를 계속 쓰면 추가 seed 불필요**.

### 19.2 프론트엔드 위치와 실행 (다른 노트북 기준)

- 코드: 레포 루트의 `frontend/` (Flutter). 상세 실행법은 `frontend/README.md`.
- 사전 조건: Flutter 3.32.8+(Dart 3.8), macOS 타깃은 Xcode/CocoaPods.
- 실행:
  ```bash
  cd frontend
  flutter pub get
  flutter run -d macos     # macOS 데스크톱 창으로 확인 (개발 결정: §아래)
  ```
- **API 주소**: `lib/core/config/app_config.dart`의 기본값이 위 Render URL로 박혀 있어 `.env` 없이 바로 붙는다.
  다른 서버로 바꾸려면 실행 시 `--dart-define=API_BASE_URL=https://...` 주입 또는 그 파일 수정.
- **개발 디바이스 = macOS 데스크톱**으로 결정함. 이유: Flutter 웹(Chrome)은 브라우저 CORS 때문에 Render 직접 호출이 막힌다(백엔드에 CORS 미들웨어 없음). 데스크톱 앱은 CORS 없음. 최종 타깃은 Android(Phase 5). macOS 아웃바운드 호출용 `network.client` 엔타이틀먼트는 이미 커밋됨(`frontend/macos/Runner/*.entitlements`).
- 백그라운드로 `flutter run` 실행 시 stdin이 TTY가 아니라 `r`(hot reload) 키가 안 먹는다. 코드 반영은 앱을 종료 후 재실행하거나, 일반 터미널에서 `flutter run` 하고 `r`/`R`을 쓴다.

### 19.3 프론트엔드 구조 (Feature 중심 + Riverpod + go_router + dio)

```text
frontend/lib/
├── main.dart                       # ProviderScope로 앱 실행
├── app/  app.dart · router.dart · theme.dart   # go_router StatefulShellRoute(하단탭)
├── core/
│   ├── config/app_config.dart      # API base URL (기본=Render, --dart-define로 override)
│   ├── network/dio_client.dart     # 백엔드 에러 봉투 {error:{code,message,details}} → ApiException
│   ├── network/api_providers.dart  # 공유 Dio provider
│   ├── errors/api_exception.dart   # 단일 에러 타입
│   ├── format/  quantity_format.dart · date_format.dart
│   └── widgets/async_view.dart     # loading/empty/error/success 공통 위젯 (spec §26.1)
└── features/
    ├── shell/home_shell.dart       # 하단 네비 홈/재고/기록/설정
    ├── home/ · settings/           # 홈/설정 (설정=현재 API 주소 표시)
    ├── history/                    # 기록 탭 (placeholder → 2-4에서 구현)
    └── inventory/
        ├── domain/  inventory_item.dart · inventory_detail.dart
        ├── data/inventory_api.dart # GET /inventory, GET /inventory/{id}
        └── presentation/
            ├── inventory_providers.dart   # list Provider + detail FutureProvider.family
            ├── inventory_list_page.dart    # 재고 목록(검색·새로고침·0수량 강조·탭→상세)
            ├── inventory_detail_page.dart  # 상세 헤더 + 최근 Event 10건
            └── event_display.dart          # Event 타입 한글 라벨/부호 색상
```

- 상태관리 Riverpod **3.x**: `StateProvider`가 기본 export에서 빠졌으니 `Notifier`/`NotifierProvider`를 쓴다(검색 상태 예시 참고).
- 새로고침은 `ref.invalidate(provider)`로 처리(당겨서 새로고침 + 버튼).
- 라우트(spec §27.1 일부): `/home`, `/inventory`, `/inventory/:itemId`, `/history`, `/settings`. `/recording`·`/action-plan/:requestId`는 Phase 3~4.

### 19.4 Phase 2 세부 우선순위 (수직 슬라이스)

| 단계 | 내용 | API | 상태 |
|---|---|---|---|
| 2-1 | 골격 + core + **재고 목록** | `GET /inventory` | ✅ 완료 (커밋 `Phase 2-1`) |
| 2-2 | **품목 상세** + 최근 Event | `GET /inventory/{id}` | ✅ 완료 (커밋 `Phase 2-2`) |
| 2-3 | **수동 입고/소비 + 목표 수량 설정** | `POST /inventory-events`(stock_in/out), `PUT /inventory/{id}/quantity` | ✅ 완료 |
| 2-4 | **기록 목록** + Event 정정/취소 | `GET /inventory-events`, `PATCH`/`DELETE /inventory-events/{id}` | ⏭ 다음 |
| 2-5 | **품목 생성/수정/보관/복원** | `POST/PATCH/DELETE /inventory-items`, `POST .../restore` | 대기 |
| 2-6 | 오류 상태·수동 새로고침 마감 + Phase 2 종료 | (횡단) | 대기 |

Phase 2 완료 기준 체크리스트: product_spec.md **§61 Phase 2 항목** 및 스펙 §68 API 계약 참조.

### 19.5 2-3 구현 결과

- 상세 화면에는 입고·소비 버튼과 전체 너비의 목표 수량 설정 버튼, 목록 각 행에는 같은 세 흐름을 여는 메뉴를 붙였다. 보관 품목에는 변경 진입점을 노출하지 않는다.
- 세 흐름은 `inventory_quantity_sheet.dart`의 공용 Bottom Sheet를 사용한다. 입고·소비는 양수 변경량, 목표 수량은 0 이상의 최종 수량을 받으며 메모는 선택이다. 기본 단위는 화면에 고정 표시하고 품목 `default_unit`을 그대로 전송한다.
- 수량은 Backend 제약과 동일하게 정수 9자리·소수 3자리까지 검증하고 JSON number로 보낸다. 수동 Event Type은 Front에서도 enum으로 `stock_in`/`stock_out`만 표현한다.
- 요청 중 입력·모드·제출 버튼을 비활성화해 중복 제출을 막는다. 서버가 음수 재고, 단위 불일치, 비활성 품목 등을 거부하면 공통 `ApiException.message`를 Sheet의 Snackbar로 표시하고 입력 상태를 유지한다.
- 성공하면 Sheet를 닫고 최종 수량을 알린 뒤 상세 Provider와 목록 Provider를 모두 invalidate한다. 목표 수량이 현재와 같아 `changed:false`이면 별도 변경 없이 이미 같은 수량임을 알린다.
- 검증(2026-07-28): Flutter 3.32.8 / Dart 3.8.1 기준 `flutter analyze` 이슈 0, `flutter test` 9 passed. API body·응답 계약, 수량 경계값, 세 모드 UI와 목표 수량 기본값을 테스트한다.
- macOS 실제 빌드/실행은 현재 작업 장비에 전체 Xcode와 CocoaPods가 없어 수행하지 못했다. 컴파일·정적 분석·Widget Test는 통과했다.

### 19.6 2-4 착수 지침 (바로 다음 작업)

- 기록 탭 placeholder를 `GET /api/v1/inventory-events` 기반 목록으로 바꾼다. 기본 정렬은 Backend 계약대로 `created_at desc`, 동일 시각 `id desc`이며 Pagination과 품목·Event Type·기간 필터를 연결한다.
- 각 기록에서 정정은 `PATCH /inventory-events/{event_id}`, 취소는 `DELETE /inventory-events/{event_id}`를 호출한다. 원본 Event를 직접 수정·삭제하는 UI나 API는 만들지 않는다.
- 정정 입력은 `stock_in`/`stock_out`, 양수 수량, 품목 기본 단위, 선택 메모만 허용한다. 성공 후 기록 목록·해당 품목 상세·재고 목록을 모두 갱신한다.
- 이미 취소된 기록, Reversal 기록, 정정 결과 음수 재고 등 Backend 거부 사유는 공통 오류 메시지로 표시하고 확인이 필요한 취소 동작에는 확인 Dialog를 둔다.

### 19.7 검증/작업 관례

- 프론트: `cd frontend && flutter analyze`(이슈 0 유지) + `flutter test`. 각 슬라이스 후 앱 재실행으로 실제 Render 데이터로 확인.
- 백엔드 변경 시: `cd backend && uv run pytest && uv run ruff check . && uv run mypy app tests`.
- Git: 슬라이스 단위 커밋(`Phase 2-N: ...`) 후 `git push origin main`. 저장소 `github.com/subeomsp/housekeeper`(main). 커밋 메시지 끝에 `Co-Authored-By: Claude ...` 유지.
- 사용자는 코드가 아니라 **제품 흐름**을 검토한다. 각 단계 완료 시 AGENTS.md의 🤖 Assistant 헤더 형식으로 화면 흐름·입출력·거부 조건 중심으로 보고한다.
- 절대 규칙: `.env`/시크릿 커밋 금지, DB 비밀번호 출력/에코 금지, 운영 Neon DB를 테스트에 사용 금지(테스트는 `TEST_DATABASE_URL`=test 브랜치).
