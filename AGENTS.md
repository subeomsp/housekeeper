# Voice Inventory Agent 작업 지침

## Source of Truth

- 프로젝트의 제품 및 구현 기준은 저장소 루트의 `product_spec.md`이다.
- 현재까지의 구현 상태와 사용자와 합의한 결정은 `HANDOFF.md`에서 확인한다.
- 구현과 문서가 충돌하면 `product_spec.md`를 우선한다.
- 문서에 없는 기능을 임의로 추가하지 않는다.
- 명세와 충돌하는 결정을 피할 수 없으면 임의로 확정하지 말고 코드 또는 문서에 TODO로 남기고 사용자에게 알린다.

## 작업 방식

- 전체 시스템을 한 번에 만들지 않고 `product_spec.md`의 구현 순서대로 Phase 단위로 진행한다.
- 각 Phase를 시작할 때 범위와 제외 대상을 먼저 확인한다.
- 기존 구조와 변경사항을 확인하고, 관련 없는 사용자 변경을 수정하거나 삭제하지 않는다.
- API나 DB 스키마를 변경할 때는 Migration과 테스트를 함께 갱신한다.
- 핵심 비즈니스 로직은 테스트 없이 완료로 처리하지 않는다.
- Secret과 실제 환경변수 값은 저장소에 커밋하지 않는다.

## 사용자 보고 형식

- 사용자에게 보내는 응답은 다음 표식으로 시작한다.

```text
━━━━━━━━━━━━━━━━━━━━

🤖 Assistant

━━━━━━━━━━━━━━━━━━━━
```

- 코드 작업 완료 보고에는 구현 결과뿐 아니라 주요 구성 요소를 어떤 책임으로 나누고 어떻게 연결했는지 간단히 설명한다.
- 구현 과정의 핵심 판단, Transaction 경계, 검증 방식처럼 전체 구성을 이해하는 데 필요한 내용을 포함한다.
- 파일별 세부 코드 설명이나 단순 작업 로그를 모두 나열하지는 않는다.
- 실행한 테스트, 정적 분석, 실제 동작 확인 결과를 구분해서 보고한다.
- API를 구현한 경우 사용자가 코드를 읽지 않고도 제품 관점에서 검토할 수 있도록 API별로 다음 내용을 보고한다.
  - 어떤 화면이나 사용자 행동을 위한 API인지
  - 언제 호출되고 무엇을 입력받아 무엇을 반환하는지
  - 내부에서 어떤 순서로 검증, 저장, 조회가 진행되는지
  - 어떤 조건에서 요청을 거부하고 사용자에게 어떤 오류를 전달하는지
  - 구현 과정에서 정한 기본값, 제한, 정렬 방식 등 제품 검토가 필요한 결정
  - 아직 연결되지 않았거나 다음 단계에서 구현할 흐름

## 현재 구현 범위: Phase 1 Backend

Phase 1의 상세 기준은 `product_spec.md` 63번부터 74번까지이다.

구현 대상:

- Python 3.12 이상과 `uv`
- FastAPI
- SQLAlchemy 2.x Async와 `asyncpg`
- Alembic
- Household, User, HouseholdMember
- InventoryItem
- Inventory Snapshot
- InventoryEvent
- AuditLog
- 개발용 Seed
- Inventory Item 생성 및 목록 API
- Inventory Item 수정, 보관 및 복원 API
- 현재 재고 및 품목 상세 조회 API
- 목표 수량 설정 API
- 수동 Inventory Event 생성 및 목록 API
- Inventory Event 정정 및 취소 API
- 품목 생성, 수정, 보관 및 복원 Audit 기록
- 음수 재고 방지
- Transaction과 Inventory Row Lock
- Snapshot 재구축 Service
- Unit Test와 Integration Test
- README와 `.env.example`

Phase 1 제외 대상:

- Flutter와 Android Widget
- 음성 녹음, STT, LLM
- Action Plan
- 사용자 초대 UI
- 단위 변환
- Event 원본의 물리 수정 및 삭제

Phase 1이 완료되기 전에는 제외 대상을 구현하지 않는다.

## 핵심 불변 규칙

- PostgreSQL이 최종 Source of Truth이다.
- 재고 변경은 반드시 InventoryEvent로 기록한다.
- Inventory 테이블은 조회용 Snapshot이며 Event 기록과 같은 Transaction에서 갱신한다.
- 재고 Event 생성 시 대상 Inventory Row를 Lock한다.
- `signed_quantity`는 클라이언트 입력을 받지 않고 Backend가 Event Type으로 계산한다.
- 출고 후 수량이 음수가 되면 Event와 Snapshot 변경을 모두 거부한다.
- Phase 1에서는 Event 단위가 품목의 `default_unit`과 정확히 같아야 한다.
- 비활성 품목 또는 다른 Household의 품목에는 Event를 생성할 수 없다.
- 품목 생성과 수량 0의 Snapshot 생성은 하나의 Transaction이다.
- 품목의 현재 수량은 직접 덮어쓰지 않고 목표 수량과의 차이를 Adjustment Event로 기록한다.
- 품목 삭제는 `is_active=false`인 Soft Delete로 처리하며 기존 Snapshot과 Event를 보존한다.
- 기본 단위 변경과 품목 보관은 현재 수량이 0일 때만 허용한다.
- Event 정정은 Reversal과 대체 Event를 만들고, Event 취소는 Reversal Event를 만든다.
- 기존 Event 원본을 수정하거나 삭제하지 않는다.
- Event 정정 및 취소와 Snapshot 갱신은 하나의 Transaction이다.
- 품목 정보 변경 History는 AuditLog에 기록하고 음성 Alias로 사용하지 않는다.
- 품목명 변경 시 이전 이름을 Alias로 자동 등록하지 않는다.
- Item Alias는 음성 품목 연결을 사용자가 승인하는 Phase 3에서 구현한다.
- API 오류는 명세 70번의 공통 Error Response 형식을 따른다.

## Backend 계층 책임

- API: 요청 파싱, 의존성 확인, Schema Validation, Service 호출, HTTP 응답 변환
- Service: 비즈니스 검증, 흐름 제어, Transaction orchestration
- Repository: ORM 조회와 저장, Lock 조회
- Model: DB 영속성 구조
- Schema: 외부 요청 및 응답 계약

API 계층에서 재고 계산이나 SQL을 직접 수행하지 않는다.

## 기본 프로젝트 구조

Backend 코드는 `backend/` 아래에 둔다. 세부 구조는 `product_spec.md` 65번을 따른다.

## 개발 및 검증 명령

명령은 특별한 사유가 없으면 `backend/`에서 실행한다.

```bash
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
uv run mypy app
```

외부 Neon 연결 정보가 없는 로컬/CI 테스트는 별도 테스트 DB 설정을 사용해야 한다. 실제 운영 DB를 테스트에 사용하지 않는다.

## 완료 기준

- 구현 기능이 `product_spec.md`의 해당 Acceptance Test를 만족한다.
- 정상 경로와 주요 실패 경로를 테스트한다.
- Migration이 빈 DB에 정상 적용된다.
- 실행법과 환경변수는 README 및 `.env.example`과 일치한다.
- 검증 명령의 실행 결과와 남은 TODO를 사용자에게 보고한다.
