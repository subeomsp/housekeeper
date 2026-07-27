# **MASTER_[SPEC.md](http://SPEC.md)**

# **Voice Inventory Agent**

### **Master Specification v1.0**

**Status** : Draft



**Purpose**



본 문서는 Voice Inventory Agent 프로젝트의 단일 Source of Truth이다.



본 프로젝트의 모든 구현은 본 문서를 기준으로 수행한다.



AI(Code Assistant), Backend, Frontend, Android Native 개발은 본 문서를 기준으로 구현한다.

---

# **1. Project Overview**

## **1.1 프로젝트명**

Voice Inventory Agent

(가칭)

---

## **1.2 프로젝트 목표**

사용자가 집에서 사용하는 식음료를 **가장 적은 노력으로 기록**할 수 있는 시스템을 만든다.

기존 재고관리 앱은 대부분 다음과 같은 과정을 요구한다.

- 앱 실행
- 품목 검색
- 수량 입력
- 저장

이 과정이 귀찮기 때문에 대부분의 사용자는 며칠 지나지 않아 사용을 중단한다.

본 프로젝트는 이러한 입력 과정을 **음성 한 번**으로 대체하는 것을 목표로 한다.

예시

사용자

우유 두 개 사왔어.

↓

AI

```
우유 +2
```

↓

사용자 확인

↓

재고 반영

---

## **1.3 핵심 가치**

이 프로젝트는 사용자가 모든 변경을 폼으로 입력해야 하는 기존 방식의 재고관리 앱이 아니다.

가장 자주 발생하는 재고 변경은 사용자가 자연스럽게 말하는 것만으로 기록할 수 있어야 한다.

정확한 확인과 예외 처리를 위해 앱의 기본 관리 기능도 함께 제공한다.

AI가

- 의도를 이해하고
- 실행 계획을 만들고
- 사용자의 승인을 받은 후
- 시스템이 재고를 수정한다.

음성은 재고 변경 Event의 생성을 가장 빠르게 만드는 핵심 기능이다.

앱의 기본 품목 및 재고 관리 기능은 그대로 제공한다.

---

# **2. Design Principle**

본 프로젝트에서 반드시 지켜야 하는 원칙이다.

## **Principle 1**

재고 변경의 기본 진입 방식은 폼 입력이 아니라 자연어 음성이다.

앱의 수동 입력과 수정 기능은 항상 보조 경로로 제공한다.

예시

```
우유 두 개 사왔어.

맥주 세 캔 마셨어.

참치캔 하나 썼어.

여보가 계란 사왔어.

우유 다 먹었네.
```

---

## **Principle 2**

LLM은

절대로 DB를 수정하지 않는다.

LLM은

오직

**Execution Plan**

만 생성한다.

---

## **Principle 3**

모든 변경은

```
음성

↓

Execution Plan

↓

사용자 확인

↓

Execute

↓

Inventory Update
```

순서로 진행된다.

---

## **Principle 4**

Inventory는 현재 값이 아니라

Event 기반으로 관리한다.

예)

현재

```
우유 3개
```

가 중요한 것이 아니라

```
+2

-1

+3

-1
```

이벤트가 원본이다.

---

## **Principle 5**

음성 입력은

앱보다 빠르게 접근 가능해야 한다.

Android Home Widget을 기본 진입점으로 사용한다.

---

# **3. MVP Scope**

이번 MVP에서 반드시 구현한다.

## **포함**

- Android 전용
- Flutter
- Kotlin Widget
- FastAPI
- PostgreSQL (Neon)
- Render
- STT
- LLM
- 음성 입력
- Execution Plan
- 재고 반영
- 현재 재고 조회
- 기록 조회
- 품목 생성, 조회, 수정, 보관 및 복원
- 현재 수량 직접 설정
- 수동 입고 및 소비
- 기록 정정 및 취소

## **제외**

- iOS
- OCR
- 영수증 인식
- 냉장고 사진 분석
- 레시피 추천
- 장보기 추천
- AI 소비 분석

---

# **4. Problem Definition**

기존 재고관리 앱은

입력 비용이 너무 크다.

사용자는

```
앱 실행

↓

검색

↓

입력

↓

저장
```

을 반복해야 한다.

결국 기록을 하지 않는다.

우리는

```
Widget

↓

말하기

↓

확인

↓

끝
```

으로 줄인다.

---

# **5. User Experience**

사용자는 재고를 빠르게 기록할 때 Widget과 음성을 우선 사용할 수 있다.

앱에서는 품목과 재고를 직접 생성, 조회, 수정, 정리할 수 있다.

음성은 기본 관리 기능을 대체하는 것이 아니라 재고 변경 Event 생성을 더 빠르게 만드는 핵심 진입 방식이다.

예)

```
홈 화면

↓

🎤

↓

우유 두 개 사왔어

↓

AI 해석

↓

확인

↓

반영
```

---

# **6. 핵심 사용자 시나리오**

## **시나리오 1**

입고

```
사용자

우유 두 개 사왔어.
```

↓

```
Execution Plan

우유

+2
```

↓

확인

↓

반영

---

## **시나리오 2**

소비

```
맥주 세 캔 마셨어.
```

↓

```
맥주

-3
```

---

## **시나리오 3**

여러 품목

```
제로콜라 한 박스 사왔고

우유 하나 마셨어.
```

↓

```
제로콜라 +24

우유 -1
```

↓

확인

↓

반영

---

## **시나리오 4**

애매한 표현

```
맥주 좀 사왔어.
```

↓

AI

```
수량을 알 수 없습니다.
```

↓

사용자 입력

↓

반영

---

## **시나리오 5**

앱에서 현재 수량 수정

```text
현재 우유 5개

↓

사용자가 수량을 2개로 설정

↓

adjustment_out 3개 Event 생성

↓

현재 우유 2개
```

Inventory Snapshot을 직접 덮어쓰지 않는다.

---

## **시나리오 6**

앱에서 잘못된 기록 정정

```text
기존 기록 우유 +20

↓

사용자가 실제 수량 +2로 정정

↓

event_reversal -20

대체 stock_in +2
```

원본 Event는 보존한다.

---

# **7. AI Principle**

AI는

해야 하는 일과

하면 안 되는 일을 명확히 구분한다.


| **AI가 하는 일**      | **AI가 하지 않는 일** |
| ----------------- | --------------- |
| 음성 해석             | DB 수정           |
| 품목 추론             | 재고 계산           |
| 단위 추론             | Execute         |
| Execution Plan 생성 | 승인 없이 반영        |
| 모호한 표현 탐지         | 현재 재고 변경        |


---

# **8. System Architecture**

```
Android Widget

↓

Recording Activity

↓

Flutter

↓

FastAPI

↓

STT

↓

LLM

↓

Execution Plan

↓

Flutter Confirm Screen

↓

Execute API

↓

PostgreSQL
```

---

# **9. Technology Stack**

Frontend

- Flutter

Android Native

- Kotlin

Backend

- FastAPI

Database

- PostgreSQL (Neon)

Deploy

- Render

AI

- Whisper 또는 OpenAI Speech-to-Text
- GPT 기반 LLM

---

# **10. 앞으로 문서에서 계속 작성할 내용**

이 문서는 이후 다음 순서대로 계속 확장한다.

1. 화면 명세(Screen Specification)
2. Android Widget 상세 설계
3. AI Prompt 및 Output Schema
4. Execution Plan 구조
5. Backend Architecture
6. API Specification
7. Database Schema
8. State Machine
9. Exception Handling
10. Deployment
11. 테스트 시나리오
12. 향후 기능(Roadmap)

이 문서는 프로젝트 진행과 함께 지속적으로 업데이트하며, 항상 최신 버전을 기준으로 구현한다.



# **11. Screen Specification**

---

# **11.1 Home Screen**

## **목적**

사용자가 현재 집에 있는 재고를 한눈에 확인할 수 있는 화면이다.

이 화면은 앱을 직접 실행했을 때 가장 먼저 보이는 화면이며, 음성 입력 외의 모든 기능의 시작점이 된다.

---

## **화면 구성**

```text
──────────────────────────

우리 집 식음료

──────────────────────────

🥛 우유             2개

🥚 계란            10개

🥤 제로콜라         8캔

🍺 맥주            15캔

...

──────────────────────────

최근 기록

우유 +2

제로콜라 -1

──────────────────────────

      🎤 음성으로 기록

──────────────────────────
```

---

## **사용자 행동**

사용자는

- 현재 재고 확인
- 품목 검색
- 음성 입력
- 최근 기록 확인

만 수행한다.

직접 수량을 수정하는 기능은 제공하지 않는다.

수정은 반드시

기록 수정

또는

Execution Plan 수정

을 통해 수행한다.

---

## **API**

GET /inventory

---

GET /inventory/recent-events

---

# **11.2 Recording Screen**

## **목적**

위젯 또는 앱에서

녹음을 수행하는 화면.

사용자가

앱을 열었다는 느낌이 들지 않을 정도로

최대한 단순해야 한다.

---

## **화면**

```text
────────────────────────

🎤

듣고 있습니다.

────────────────────────

"우유 두 개 사왔어."

────────────────────────

[중지]

────────────────────────
```

---

## **동작**

화면이 열리면

자동으로 녹음을 시작한다.

사용자가

중지 버튼을 누르거나

일정 시간 침묵하면

자동 종료한다.

---

## **상태**

Recording

↓

Uploading

↓

Transcribing

↓

Planning

↓

Execution Plan

---

# **11.3 Execution Plan Screen**

## **목적**

AI가 이해한 내용을

사용자에게 보여주는 화면.

절대로

바로 Execute하지 않는다.

반드시

사용자가 확인한다.

---

## **화면**

```text
────────────────────────

이렇게 이해했습니다.

────────────────────────

＋ 우유 2개

－ 제로콜라 1캔

────────────────────────

[수정]

[삭제]

────────────────────────

[취소]

[반영]

────────────────────────
```

---

## **사용자 행동**

각 Action은

개별 수정 가능.

예)

우유

↓

품목 변경

↓

수량 변경

↓

단위 변경

---

## **Execute**

반영 버튼을 누르면

Execute API 호출.

---

# **11.4 Inventory Screen**

## **목적**

전체 재고 조회.

---

## **기능**

검색

필터

카테고리

정렬

품목 직접 추가

품목 보관 여부 표시

---

예)

```text
우유

현재

2개

위치

냉장고

최근 수정

오늘
```

---

품목을 누르면

상세 화면 이동.

---

# **11.5 Item Detail**

표시

현재 수량

최근 변경

최근 소비

최근 입고

사용자 행동

- 품목명 및 카테고리 수정
- 기본 단위 수정
- 현재 수량 직접 설정
- 수동 입고 및 소비
- 품목 보관 및 복원

현재 수량 직접 설정은 Inventory Snapshot 수정이 아니다.

Backend가 현재 수량과 목표 수량의 차이를 계산하여 `adjustment_in` 또는 `adjustment_out` Event를 생성한다.

기본 단위 변경과 품목 보관은 현재 수량이 0일 때만 허용한다.

---

예)

```text
우유

현재

2개

──────────

7/20

+2

──────────

7/18

-1

──────────

7/15

+3
```

---

# **11.6 History Screen**

모든 이벤트 조회.

Event Sourcing 로그.

예)

```text
오늘

우유 +2

제로콜라 -1

계란 +10

어제

맥주 -3

참치 +4
```

---

잘못된 기록은 정정하거나 취소할 수 있다.

정정은 원본 Event를 직접 수정하지 않고 `event_reversal`과 대체 Event를 하나의 Transaction으로 생성한다.

취소는 원본 Event를 직접 삭제하지 않고 `event_reversal`을 생성한다.

---

# **12. Android Widget**

## **목표**

사용자가

앱을 열지 않고

음성을 입력한다.

---

## **위젯 구성**

```text
┌───────────────┐

🎤 재고 기록

└───────────────┘
```

---

## **Flow**

Widget Click

↓

Recording Activity

↓

자동 녹음

↓

STT

↓

Planning

↓

Flutter Confirm

---

## **특징**

앱을 탐색하지 않는다.

버튼 하나.

녹음 자동 시작.

---

# **13. Recording Pipeline**

```text
Widget

↓

Recording

↓

Audio File

↓

Upload

↓

Speech To Text

↓

Transcript

↓

LLM

↓

Execution Plan

↓

User Confirm

↓

Execute

↓

Inventory Update

↓

Done
```

---

# **14. AI Design**

AI는

재고관리 시스템이 아니다.

AI는

Execution Planner이다.

---

## **입력**

Transcript

현재 품목 목록

단위 정보

사용자 사전

---

## **출력**

Execution Plan

---

예)

사용자

```text
제로콜라 한 박스 사왔고

우유 하나 마셨어.
```

↓

AI

```json
{
  "requires_confirmation": true,
  "actions": [
    {
      "type": "stock_in",
      "item": "제로콜라",
      "quantity": 24,
      "unit": "캔"
    },
    {
      "type": "stock_out",
      "item": "우유",
      "quantity": 1,
      "unit": "개"
    }
  ]
}
```

---

AI는

현재 재고를 수정하지 않는다.

Execute하지 않는다.

DB를 수정하지 않는다.

Execution Plan만 생성한다.

---

# **15. Execution Plan**

Execution Plan은

AI와 Backend의 계약이다.

Backend는

Execution Plan만 신뢰한다.

Transcript는

참고용이다.

---

Execution Plan 구조

```text
Request

↓

Transcript

↓

Actions[]

↓

Validation

↓

User Confirm

↓

Execute
```

---

모든 Action은

독립적으로 수정 가능해야 한다.

예)

Action 1

우유 +2

Action 2

제로콜라 -1

사용자는

Action 2만 삭제 가능해야 한다.



# **16. Backend Architecture**

## **16.1 Backend 역할**

Backend는 시스템의 유일한 Source of Truth이다.

AI는 자연어를 이해하고 Execution Plan을 생성하지만, 실제 데이터 변경은 Backend만 수행한다.

Backend의 책임은 다음과 같다.

- 재고 조회
- Execution Plan 검증
- 재고 변경 실행
- Event 저장
- 현재 재고 계산
- 동시성 제어
- Household 권한 검증
- Audit Log 저장

Backend는 AI의 결과를 그대로 신뢰하지 않는다.

모든 Execution Plan은 서버에서 다시 검증한 후 실행한다.

---

## **16.2 Architecture**

```text
Flutter

↓

FastAPI

↓

Service Layer

↓

Repository Layer

↓

PostgreSQL
```

LLM은 Backend 외부 서비스이며,

Backend는 LLM의 결과를 입력값 중 하나로만 취급한다.

---

# **17. API Specification**

## **17.1 음성 업로드**

POST

```text
/api/v1/voice-request
```

### **목적**

음성을 업로드하여 Execution Plan을 생성한다.

### **Request**

multipart/form-data

```text
audio.wav
```

또는

```json
{
    "audio_url": "..."
}
```

---

### **Response**

```json
{
  "request_id": "req_xxx",

  "transcript": "우유 두 개 사왔고 콜라 하나 마셨어.",

  "requires_confirmation": true,

  "actions":[
    {
      "action_id":"a1",
      "type":"stock_in",
      "item":"우유",
      "quantity":2,
      "unit":"개",
      "confidence":0.99
    },
    {
      "action_id":"a2",
      "type":"stock_out",
      "item":"제로콜라",
      "quantity":1,
      "unit":"캔",
      "confidence":0.96
    }
  ]
}
```

Backend는 DB를 수정하지 않는다.

Execution Plan만 반환한다.

---

## **17.2 Execute**

POST

```text
/api/v1/action-plan/{request_id}/execute
```

### **목적**

사용자가 승인한 Execution Plan을 실제 반영한다.

---

### **Request**

```json
{
  "actions":[
    {
      "action_id":"a1",
      "item":"우유",
      "quantity":2,
      "unit":"개"
    },
    {
      "action_id":"a2",
      "item":"제로콜라",
      "quantity":1,
      "unit":"캔"
    }
  ]
}
```

사용자가 수정했다면 수정된 값을 전달한다.

---

### **Response**

```json
{
    "success":true,

    "inventory_updated":true,

    "event_count":2
}
```

---

## **17.3 현재 재고 조회**

GET

```text
/api/v1/inventory
```

Response

```json
[
  {
    "item":"우유",
    "quantity":2,
    "unit":"개"
  },
  {
    "item":"계란",
    "quantity":10,
    "unit":"개"
  }
]
```

---

## **17.4 품목 상세**

GET

```text
/api/v1/inventory/{item_id}
```

현재 수량

최근 변경

최근 이벤트 반환

---

## **17.5 이벤트 조회**

GET

```text
/api/v1/inventory-events
```

최근 변경 내역 반환

---

## **17.6 이벤트 정정**

PATCH

```text
/api/v1/inventory-events/{event_id}
```

잘못 입력된 기록을 정정한다.

기존 Event Row는 직접 수정하지 않는다.

정정 Transaction에서 다음 Event를 생성한다.

```text
기존 Event의 반대값을 가진 event_reversal

새 값을 가진 대체 Event
```

수정 후 Inventory Snapshot을 함께 갱신한다.

---

## **17.7 이벤트 취소**

DELETE

```text
/api/v1/inventory-events/{event_id}
```

기존 Event를 물리 삭제하지 않는다.

`event_reversal`을 생성하고 Inventory Snapshot을 같은 Transaction에서 갱신한다.

---

## **17.8 품목 및 수량 수동 관리**

앱에서는 다음 작업을 API로 제공한다.

```text
품목 생성

품목 정보 수정

품목 보관 및 복원

현재 수량 설정

수동 입고 및 소비
```

현재 수량 설정은 목표 수량과 현재 수량의 차이만큼 Adjustment Event를 생성한다.

---

# **18. Database Design**

## **설계 원칙**

Inventory는 Event에서 계산된다.

현재 수량은

조회 성능을 위해 캐시 형태로 유지한다.

실제 원본 데이터는 Event이다.

---

## **ERD**

```text
Household

↓

User

↓

Inventory Item

↓

Inventory Event

↓

Voice Request
```

---

# **18.1 households**

```text
id

name

created_at
```

---

# **18.2 users**

```text
id

household_id

nickname

created_at
```

---

# **18.3 inventory_items**

품목 마스터

```text
id

household_id

name

default_unit

category

created_at
```

예)

우유

계란

제로콜라

참치

---

# **18.4 inventory**

현재 재고

```text
id

item_id

quantity

updated_at
```

조회 성능을 위한 테이블이다.

---

# **18.5 inventory_events**

가장 중요한 테이블

```text
id

household_id

item_id

type

quantity

unit

voice_request_id

created_by

created_at
```

예)

```text
우유

+2
```

또는

```text
맥주

-3
```

---

# **18.6 voice_requests**

사용자가 말한 원문 저장

```text
id

transcript

audio_path

status

created_at
```

---

# **18.7 action_plans**

LLM 결과 저장

```text
id

voice_request_id

json

approved

executed

created_at
```

---

# **19. Transaction Rule**

Execute는 반드시 하나의 Transaction으로 수행한다.

```text
BEGIN

↓

Inventory Event Insert

↓

Inventory Update

↓

Audit Log

↓

Commit
```

중간에 실패하면

ROLLBACK.

---

# **20. State Machine**

Voice Request

```text
Recording

↓

Uploading

↓

Transcribing

↓

Planning

↓

Waiting Confirmation

↓

Executing

↓

Completed
```

---

Execution

```text
Created

↓

Approved

↓

Executing

↓

Completed
```

---

# **21. Validation Rule**

Backend는 다음을 검증한다.

### **품목 존재 여부**

없으면

신규 품목 생성 여부 확인

---

### **수량**

0 이하 불가

---

### **단위**

허용된 단위인지 확인

예)

개

캔

병

봉

박스

L

ml

g

kg

---

### **Household 권한**

다른 Household 데이터 접근 금지

---

# **22. Event Sourcing**

Inventory는

절대로 직접 수정하지 않는다.

항상 Event를 추가한다.

예)

현재

```text
우유

5개
```

사용자

```text
우유 두 개 마셨어.
```

저장

```text
-2
```

Inventory는

자동 계산

↓

3개

---

이 방식을 선택한 이유

- Undo 가능
- History 유지
- Audit 가능
- 통계 가능
- AI 학습 가능

---

# **23. Error Handling**

## **음성 인식 실패**

사용자에게

다시 녹음 요청

---

## **품목 미인식**

후보 제시

예)

```text
우유

↓

서울우유

매일우유

상하목장
```

---

## **수량 미확인**

예)

```text
맥주 사왔어.
```

↓

수량 입력 요청

---

## **단위 미확인**

예)

```text
참치 많이 샀어.
```

↓

몇 개인가요?

---

## **Confidence가 낮은 경우**

Execution Plan에

경고 표시

사용자가 반드시 수정하도록 유도한다.

---

# **24. Backend Design Principle**

Backend는 AI를 신뢰하지 않는다.

AI는 Backend를 대체하지 않는다.

Backend는 항상

- Validation
- Authorization
- Transaction
- Data Integrity

를 책임진다.

LLM은

Execution Planner일 뿐이다.



# **25. Frontend Architecture**

## **25.1 Frontend 역할**

Flutter 앱은 다음을 담당한다.

- 현재 재고 조회 및 표시
- 품목 상세 조회
- 기록 내역 조회
- 음성 입력 진입
- 음성 처리 상태 표시
- Execution Plan 확인
- Action 수정 및 삭제
- 사용자 승인 및 실행 요청
- 실행 결과 표시
- 오류 및 재시도 UI

Flutter는 직접 PostgreSQL에 접근하지 않는다.

모든 데이터는 FastAPI를 통해 조회하거나 변경한다.

---

## **25.2 Flutter Architecture**

Flutter 프로젝트는 Feature 중심 구조를 사용한다.

```text
lib/
├── app/
│   ├── app.dart
│   ├── router.dart
│   └── theme.dart
│
├── core/
│   ├── api/
│   ├── config/
│   ├── errors/
│   ├── network/
│   ├── storage/
│   └── widgets/
│
├── features/
│   ├── inventory/
│   ├── voice_recording/
│   ├── action_plan/
│   ├── history/
│   └── household/
│
└── main.dart
```

각 Feature는 다음 구조를 기본으로 한다.

```text
feature/
├── data/
│   ├── api/
│   ├── dto/
│   └── repository_impl/
│
├── domain/
│   ├── entities/
│   ├── repositories/
│   └── usecases/
│
└── presentation/
    ├── pages/
    ├── widgets/
    └── providers/
```

MVP에서는 과도한 계층화를 피할 수 있다.

단, 다음 항목은 반드시 분리한다.

- API DTO
- 화면 상태
- 비즈니스 모델
- API 호출 코드
- 화면 위젯

---

# **26. State Management**

상태 관리는 Riverpod을 기본 선택으로 한다.

선택 이유는 다음과 같다.

- 비동기 상태 관리가 단순하다.
- API 요청 상태를 명확하게 표현할 수 있다.
- 화면과 로직을 분리하기 쉽다.
- 테스트가 가능하다.
- Provider 간 의존성을 관리하기 쉽다.

주요 상태는 다음과 같다.

```text
InventoryState

VoiceRequestState

ActionPlanState

HistoryState

HouseholdState
```

---

## **26.1 공통 비동기 상태**

모든 API 기반 화면은 다음 상태를 가진다.

```text
initial

loading

success

empty

error
```

예를 들어 재고 조회 실패 시 빈 목록으로 처리하지 않는다.

반드시 error 상태를 표시한다.

---

# **27. Navigation**

앱의 기본 화면 구조는 Bottom Navigation을 사용한다.

```text
홈

재고

기록

설정
```

음성 기록은 중앙 Floating Action Button 또는 홈 화면의 고정 버튼으로 제공한다.

위젯에서 앱으로 진입한 경우에는 일반 홈 화면이 아니라 바로 녹음 또는 Execution Plan 화면으로 이동한다.

---

## **27.1 Route 정의**

```text
/home

/inventory

/inventory/:itemId

/history

/recording

/action-plan/:requestId

/settings
```

Android Widget으로부터 전달된 Intent에 `request_id`가 포함된 경우 다음 Route로 이동한다.

```text
/action-plan/{request_id}
```

녹음 시작 요청이면 다음 Route로 이동한다.

```text
/recording?autoStart=true
```

---

# **28. Flutter Screen Detail**

## **28.1 HomePage**

### **표시 정보**

- Household 이름
- 재고 부족 품목
- 최근 변경 품목
- 최근 기록
- 음성 기록 버튼

### **API**

```text
GET /api/v1/inventory?limit=10
GET /api/v1/inventory-events?limit=5
```

### **사용자 행동**

- 품목 선택
- 품목 직접 추가
- 전체 재고 보기
- 기록 보기
- 음성 기록 시작

---

## **28.2 InventoryPage**

### **기능**

- 전체 품목 조회
- 검색
- 카테고리 필터
- 수량 0 품목 포함 여부
- 보관 품목 포함 여부
- 이름순 정렬
- 최근 변경순 정렬
- 품목 직접 추가

### **API**

```text
GET /api/v1/inventory
```

### **Query Parameter 예시**

```text
search=우유
category=drink
include_zero=true
sort=updated_at
order=desc
```

---

## **28.3 ItemDetailPage**

### **표시 정보**

- 품목명
- 현재 수량
- 기본 단위
- 카테고리
- 최근 이벤트
- 마지막 변경 시간

### **사용자 행동**

- 품목명과 카테고리 수정
- 현재 수량 직접 설정
- 수동 입고
- 수동 소비
- 기본 단위 수정
- 품목 보관 및 복원

현재 수량 설정 화면은 목표 수량을 입력받는다.

Flutter는 수량 차이나 `signed_quantity`를 계산하지 않고 목표 수량만 Backend에 전달한다.

기본 단위 수정과 품목 보관은 현재 수량이 0일 때만 가능하다는 안내를 표시한다.

### **API**

```text
GET /api/v1/inventory/{item_id}
GET /api/v1/inventory-events?item_id={item_id}
PATCH /api/v1/inventory-items/{item_id}
DELETE /api/v1/inventory-items/{item_id}
POST /api/v1/inventory-items/{item_id}/restore
PUT /api/v1/inventory/{item_id}/quantity
POST /api/v1/inventory-events
```

---

## **28.3.1 HistoryPage**

### **표시 정보**

- Event 발생 시간
- 품목명
- Event Type
- 원래 수량
- 계산 수량
- 작성 방식
- 정정 및 취소 여부

### **사용자 행동**

- 잘못된 Event 정정
- Event 취소

정정 및 취소 화면은 원본 Event가 삭제되지 않고 이력이 보존된다는 점을 안내한다.

### **API**

```text
GET /api/v1/inventory-events
PATCH /api/v1/inventory-events/{event_id}
DELETE /api/v1/inventory-events/{event_id}
```

---

## **28.4 RecordingPage**

### **진입 방식**

- 앱 내부 버튼
- Android Home Widget
- 알림 Action
- Android Shortcut

### **동작**

화면 진입 시 `autoStart=true`이면 즉시 녹음을 시작한다.

### **상태 UI**

```text
permission_required

ready

recording

uploading

transcribing

planning

completed

failed
```

### **Recording 상태**

```text
듣고 있어요

00:04

[중지]
```

### **Uploading 상태**

```text
음성을 전송하고 있어요.
```

### **Transcribing 상태**

```text
말한 내용을 확인하고 있어요.
```

### **Planning 상태**

```text
재고 변경 내용을 정리하고 있어요.
```

### **Failed 상태**

```text
음성을 처리하지 못했어요.

[다시 녹음]
```

---

## **28.5 ActionPlanPage**

이 화면은 MVP의 핵심 화면이다.

### **표시 정보**

- 원본 Transcript
- Action 목록
- Action별 경고
- Action별 Confidence
- 전체 취소
- 전체 실행

### **Action Card**

```text
＋ 우유

수량: 2

단위: 개

[수정] [삭제]
```

### **경고 Action**

```text
＋ 제로콜라

수량: 1박스

한 박스를 24캔으로 해석했어요.

[수정 필요]
```

### **사용자 행동**

- 품목 변경
- 수량 변경
- 단위 변경
- Action Type 변경
- Action 삭제
- 전체 취소
- 실행

---

# **29. Action Edit UI**

Action Card를 누르면 Bottom Sheet를 연다.

```text
품목

[우유                ]

작업

[입고 ▼]

수량

[2]

단위

[개 ▼]

[삭제]          [완료]
```

---

## **29.1 품목 선택**

품목 입력 시 기존 품목을 검색한다.

기존 품목이 없으면 신규 품목 생성 옵션을 보여준다.

```text
검색 결과가 없습니다.

“아몬드브리즈”를 새 품목으로 추가
```

신규 품목에는 다음 정보가 필요하다.

- 품목명
- 기본 단위
- 카테고리

MVP에서는 카테고리는 선택 사항이다.

---

## **29.2 Action Type**

허용 값은 다음과 같다.

```text
stock_in

stock_out

set_quantity
```

MVP 기본 입력은 `stock_in`, `stock_out`이다.

`set_quantity`는 다음과 같은 표현에서 사용한다.

```text
우유 이제 하나 남았어.

맥주 재고가 5캔이야.

계란 다 먹었어.
```

예시

```json
{
  "type": "set_quantity",
  "item": "우유",
  "quantity": 1,
  "unit": "개"
}
```

`set_quantity`도 승인 후 Backend가 보정 Event로 변환하여 저장한다.

---

# **30. Android Native Architecture**

## **30.1 Kotlin 역할**

Kotlin Native 코드는 다음 기능만 담당한다.

- Android Home Widget
- Widget Click 처리
- 녹음 전용 Activity 실행
- 마이크 권한 확인
- 녹음 시작 및 종료
- Foreground Service 관리
- 음성 파일 생성
- Flutter Activity 실행
- Flutter에 진입 파라미터 전달

재고 화면과 Execution Plan 화면은 Flutter로 구현한다.

---

## **30.2 Android 구성 요소**

```text
InventoryWidgetProvider

WidgetRecordingActivity

AudioRecordingService

MainActivity

Flutter MethodChannel
```

---

## **30.3 InventoryWidgetProvider**

홈 화면 Widget을 관리한다.

### **Widget UI**

```text
┌──────────────────┐
│  🎤 재고 기록     │
└──────────────────┘
```

MVP에서는 버튼 하나만 제공한다.

### **클릭 동작**

Widget 클릭 시 `PendingIntent`를 통해 `WidgetRecordingActivity`를 실행한다.

Intent Extra 예시

```text
source=home_widget
auto_start_recording=true
```

---

# **31. Widget Recording Flow**

```text
Widget Click

↓

WidgetRecordingActivity 실행

↓

마이크 권한 확인

↓

녹음 시작

↓

사용자 중지 또는 침묵 감지

↓

파일 저장

↓

Voice Request API 호출

↓

request_id 수신

↓

Flutter ActionPlanPage 실행
```

---

## **31.1 위젯에서 즉시 녹음할 때의 원칙**

사용자가 위젯을 눌렀더라도 다음 사항은 반드시 지킨다.

- 녹음 중임을 화면에 표시한다.
- Android 마이크 사용 표시를 숨기지 않는다.
- Foreground Service 알림을 제공한다.
- 사용자가 언제든 녹음을 종료할 수 있어야 한다.
- 사용자 동의 없이 지속적으로 녹음하지 않는다.

---

# **32. WidgetRecordingActivity**

## **목적**

Flutter 전체 앱이 로딩되기 전에 빠르게 녹음을 시작한다.

## **UI**

투명 Activity보다는 작은 전용 Activity를 권장한다.

```text
────────────────────

🎤 듣고 있어요

“우유 두 개 사왔어”

00:04

[취소]       [완료]

────────────────────
```

### **완료**

- 녹음 종료
- 음성 파일 저장
- 서버 업로드
- Flutter 실행

### **취소**

- 녹음 파일 삭제
- Activity 종료
- 서버 호출하지 않음

---

# **33. Audio Recording Service**

녹음은 Foreground Service에서 수행한다.

### **책임**

- MediaRecorder 또는 AudioRecord 시작
- 음성 파일 저장
- 녹음 시간 관리
- 최대 녹음 시간 제한
- 오류 처리
- Foreground Notification 표시

### **기본 제한**

```text
최대 녹음 시간: 30초

최소 녹음 시간: 0.5초

권장 포맷: m4a 또는 wav
```

음성 인식 API가 지원하는 포맷을 기준으로 최종 결정한다.

---

## **33.1 Silence Detection**

MVP 1차 버전에서는 자동 침묵 감지를 제외해도 된다.

초기 구현은 다음과 같이 단순화한다.

```text
Widget 클릭

↓

녹음 시작

↓

사용자가 완료 버튼 클릭

↓

녹음 종료
```

자동 종료는 후속 버전에서 추가한다.

자동 종료를 구현할 경우 다음 기준을 사용할 수 있다.

```text
최소 발화 이후

1.5~2초 이상 무음

↓

녹음 종료
```

---

# **34. Flutter Native Bridge**

Flutter와 Kotlin 간에는 MethodChannel을 사용한다.

Channel 이름 예시

```text
voice_inventory/native
```

---

## **34.1 Kotlin → Flutter**

Flutter 실행 시 Intent Extra로 다음 값을 전달한다.

```json
{
  "source": "home_widget",
  "request_id": "req_xxx",
  "initial_route": "action_plan"
}
```

Flutter는 앱 시작 시 Extra를 읽고 적절한 화면으로 이동한다.

---

## **34.2 Flutter → Kotlin**

Flutter에서 Android 녹음 기능을 호출할 수 있다.

Method 예시

```text
startRecording

stopRecording

cancelRecording

getRecordingStatus
```

MVP에서는 앱 내부 녹음도 Kotlin Recording 모듈을 재사용하도록 한다.

---

# **35. Backend Project Structure**

FastAPI 프로젝트는 다음 구조를 기본으로 한다.

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── dependencies.py
│   │   └── v1/
│   │       ├── inventory.py
│   │       ├── events.py
│   │       ├── voice_requests.py
│   │       ├── action_plans.py
│   │       └── households.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── exceptions.py
│   │
│   ├── models/
│   │   ├── household.py
│   │   ├── user.py
│   │   ├── inventory_item.py
│   │   ├── inventory.py
│   │   ├── inventory_event.py
│   │   ├── voice_request.py
│   │   └── action_plan.py
│   │
│   ├── schemas/
│   │   ├── inventory.py
│   │   ├── events.py
│   │   ├── voice.py
│   │   └── action_plan.py
│   │
│   ├── repositories/
│   │
│   ├── services/
│   │   ├── inventory_service.py
│   │   ├── voice_service.py
│   │   ├── action_plan_service.py
│   │   ├── stt_service.py
│   │   └── llm_service.py
│   │
│   └── prompts/
│       └── inventory_planner.txt
│
├── migrations/
├── tests/
├── pyproject.toml
└── Dockerfile
```

---

# **36. Backend Layer Responsibility**

## **API Layer**

담당

- Request 파싱
- 인증 사용자 확인
- Schema Validation
- Service 호출
- HTTP Response 반환

담당하지 않음

- 재고 계산
- SQL 직접 작성
- LLM Prompt 생성
- Transaction 처리

---

## **Service Layer**

담당

- 비즈니스 흐름
- Validation
- Transaction orchestration
- Execution Plan 검증
- 재고 변경 실행

---

## **Repository Layer**

담당

- 데이터 조회
- 데이터 저장
- Lock 조회
- ORM 처리

---

## **AI Adapter Layer**

담당

- STT Provider 호출
- LLM Provider 호출
- Structured Output 검증
- Provider별 응답 형식 통일

---

# **37. LLM Provider Adapter**

특정 AI Provider에 직접 종속되지 않도록 Adapter를 둔다.

```text
LLMProvider

├── OpenAILLMProvider

├── GeminiLLMProvider

└── LocalLLMProvider
```

공통 Interface 예시

```python
class InventoryPlannerProvider:
    async def create_action_plan(
        self,
        transcript: str,
        inventory_context: list[dict],
    ) -> ActionPlanResult:
        ...
```

STT도 동일하게 Provider Interface를 둔다.

```python
class SpeechToTextProvider:
    async def transcribe(self, audio_path: str) -> str:
        ...
```

---

# **38. Action Plan Schema**

AI가 반환하는 최종 출력 형식이다.

```json
{
  "version": "1.0",
  "transcript": "제로콜라 한 박스 사왔고 우유 하나 마셨어.",
  "summary": "제로콜라 입고 및 우유 소비",
  "requires_confirmation": true,
  "actions": [
    {
      "action_id": "a1",
      "type": "stock_in",
      "item": {
        "raw_name": "제로콜라",
        "matched_item_id": "item_001",
        "matched_name": "코카콜라 제로",
        "is_new_item": false
      },
      "quantity": {
        "raw_value": 1,
        "raw_unit": "박스",
        "normalized_value": 24,
        "normalized_unit": "캔",
        "conversion_applied": true,
        "conversion_reason": "기존 품목 설정에서 1박스는 24캔"
      },
      "confidence": 0.92,
      "warnings": [
        {
          "code": "UNIT_CONVERSION_APPLIED",
          "message": "한 박스를 24캔으로 해석했어요."
        }
      ],
      "requires_user_input": false
    },
    {
      "action_id": "a2",
      "type": "stock_out",
      "item": {
        "raw_name": "우유",
        "matched_item_id": "item_002",
        "matched_name": "우유",
        "is_new_item": false
      },
      "quantity": {
        "raw_value": 1,
        "raw_unit": "개",
        "normalized_value": 1,
        "normalized_unit": "개",
        "conversion_applied": false,
        "conversion_reason": null
      },
      "confidence": 0.98,
      "warnings": [],
      "requires_user_input": false
    }
  ]
}
```

---

# **39. Action Plan Validation**

Backend는 AI 출력 후 다음 항목을 검증한다.

- `version`이 지원되는 버전인가
- `actions`가 비어 있지 않은가
- Action Type이 허용된 값인가
- 수량이 숫자인가
- 수량이 0보다 큰가
- 단위가 허용된 값인가
- matched item이 해당 Household 소속인가
- 중복 Action이 존재하는가
- 신규 품목 생성에 필수 정보가 있는가
- `stock_out` 실행 시 음수 재고 정책에 위배되는가

검증 실패 시 실행 가능한 Plan으로 저장하지 않는다.

---

# **40. Confidence Rule**

Confidence는 UI 표시와 검토 필요 여부 판단에 사용한다.

```text
0.90 이상

높음

기본 확인만 필요
```

```text
0.70 이상 0.90 미만

보통

경고 표시
```

```text
0.70 미만

낮음

사용자 수정 필수
```

단, Confidence만으로 자동 실행하지 않는다.

모든 Action Plan은 사용자의 명시적 승인을 받아야 한다.

---

# **41. AI Prompt Principle**

System Prompt에는 다음 원칙을 포함한다.

```text
당신은 가정용 식음료 재고관리 시스템의 Execution Planner이다.

당신은 사용자의 발화를 재고 변경 실행계획으로 변환한다.

당신은 실제 재고를 변경하지 않는다.

당신은 현재 재고를 임의로 계산하지 않는다.

사용자의 발화에 없는 수량을 임의로 생성하지 않는다.

모호한 정보는 requires_user_input=true로 반환한다.

한 문장에 여러 품목이 있으면 여러 Action으로 분리한다.

반드시 지정된 JSON Schema만 반환한다.
```

---

## **41.1 금지 규칙**

AI는 다음 행동을 하면 안 된다.

- 승인 여부를 대신 판단
- DB 수정 명령 생성
- 존재하지 않는 품목 ID 생성
- 불명확한 수량을 임의 추정
- 사용자의 발화에 없는 구매나 소비 생성
- 재고 부족을 이유로 Action 삭제
- 자연어 설명만 반환
- JSON 외의 문자열 반환

---

# **42. Unit Conversion**

단위 변환은 LLM이 임의로 결정하지 않는다.

우선순위는 다음과 같다.

```text
1. Household Item Unit Rule

2. 사용자 확인 이력

3. 기본 단위 사전

4. 확인 필요
```

예시

```text
제로콜라

1박스 = 24캔
```

```text
생수

1묶음 = 6병
```

```text
계란

1판 = 30개
```

품목별 변환 규칙이 없는 경우 다음과 같이 반환한다.

```json
{
  "raw_value": 1,
  "raw_unit": "박스",
  "normalized_value": null,
  "normalized_unit": null,
  "requires_user_input": true
}
```

---

# **43. Additional Database Tables**

## **43.1 item_aliases**

사용자가 같은 품목을 다르게 말하는 표현을 연결한다.

Alias는 품목명 변경 History가 아니다.

```text
id

household_id

inventory_item_id

alias

normalized_alias

source

created_at
```

예시

```text
코카콜라 제로

제로콜라

콜라제로
```

허용 `source`:

```text
manual

voice_confirmation

system
```

같은 Household에서 하나의 Alias가 여러 품목을 가리키지 않도록 한다.

```text
UNIQUE (household_id, normalized_alias)
```

품목명을 수정해도 기존 이름을 Alias로 자동 등록하지 않는다.

음성 입력을 사용자가 특정 품목과 직접 연결하고 기억하기를 승인했을 때 Alias로 저장한다.

음성 품목 매칭 순서:

```text
현재 normalized_name 정확 일치

↓

normalized_alias 정확 일치

↓

후보 추론 및 사용자 확인
```

---

## **43.2 item_unit_conversions**

품목별 단위 변환 규칙이다.

```text
id

inventory_item_id

from_unit

to_unit

multiplier

created_at

updated_at
```

예시

```text
제로콜라

박스

캔

24
```

---

## **43.3 action_plan_items**

Action Plan 내부 Action을 JSON 하나로만 저장하지 않고 개별 Row로 관리할 수 있다.

```text
id

action_plan_id

sequence

action_type

item_id

raw_item_name

quantity

unit

normalized_quantity

normalized_unit

confidence

requires_user_input

warning_json

created_at
```

MVP에서는 `action_plans.payload_json`으로 시작할 수 있다.

Action 단위 검색과 분석이 필요해지면 별도 테이블로 분리한다.

---

## **43.4 audit_logs**

Audit Log는 품목 정보와 시스템 상태가 변경된 사실을 추적한다.

음성 품목 매칭에는 사용하지 않는다.

```text
id

household_id

user_id

action

target_type

target_id

before_json

after_json

created_at
```

주요 기록 대상

- Action Plan 승인
- Inventory Event 생성
- Event 정정
- Event 취소
- 신규 품목 생성
- 품목명, 기본 단위, 카테고리 수정
- 품목 보관 및 복원

품목명 변경 시:

```text
inventory_items.name
= 현재 공식 이름

audit_logs.before_json / after_json
= 변경 전후 정보

item_aliases
= 자동 변경 없음
```

---

# **44. Inventory Event Type**

허용 Event Type은 다음과 같다.

```text
stock_in

stock_out

adjustment_in

adjustment_out

initial_stock

event_reversal
```

`set_quantity`는 직접 Event Type으로 저장하지 않는다.

현재 수량과 목표 수량의 차이를 계산하여 다음 중 하나로 변환한다.

```text
adjustment_in

adjustment_out
```

예시

현재 우유 수량

```text
3개
```

사용자

```text
우유 이제 1개 남았어.
```

실행 결과

```text
adjustment_out -2
```

---

# **45. Event Correction Rule**

기존 Event는 직접 수정하거나 물리 삭제하지 않는다.

잘못된 Event는 반대 Event를 생성하여 취소한다.

예시

기존 오류

```text
우유 +20
```

실제 값

```text
우유 +2
```

수정 시

```text
event_reversal -20

대체 stock_in +2
```

기존 Event에는 다음 값을 기록한다.

```text
reversed_at

reversed_by

reversal_event_id
```

이 방식으로 원본 기록과 수정 이력을 모두 보존한다.

Event 정정은 다음 작업을 하나의 Transaction으로 수행한다.

```text
정정 대상 Event 및 Inventory Row Lock

↓

대상 Event의 반대 signed_quantity를 가진 event_reversal 생성

↓

사용자가 입력한 대체 Event 생성

↓

Inventory Snapshot 갱신

↓

원본 Event에 reversed_at, reversed_by, reversal_event_id 기록
```

Event 취소는 대체 Event 없이 `event_reversal`만 생성한다.

이미 취소된 Event와 `event_reversal` Event는 다시 정정하거나 취소할 수 없다.

정정 또는 취소 결과가 음수 재고를 만들면 전체 Transaction을 거부한다.

---

# **46. Negative Inventory Policy**

MVP 기본 정책은 음수 재고를 허용하지 않는다.

현재 재고보다 많이 소비하려는 경우 실행을 차단한다.

예시

```text
현재 맥주 2캔

사용자 입력

맥주 3캔 마셨어.
```

결과

```text
현재 재고보다 소비 수량이 많습니다.

현재 재고를 0으로 변경하거나

기록을 수정해 주세요.
```

후속 버전에서는 Household 설정으로 음수 재고를 허용할 수 있다.

---

# **47. Idempotency**

Execute API는 중복 실행을 방지해야 한다.

Request Header 또는 Body에 `idempotency_key`를 포함한다.

```json
{
  "idempotency_key": "req_xxx_execution_001",
  "actions": []
}
```

동일 Key로 이미 실행된 요청이면 기존 실행 결과를 반환한다.

새로운 Inventory Event를 다시 생성하지 않는다.

---

# **48. Concurrency Control**

두 사용자가 동시에 같은 품목을 수정할 수 있다.

Execute 시 다음 절차를 따른다.

```text
Transaction 시작

↓

Inventory Row SELECT FOR UPDATE

↓

현재 수량 재확인

↓

Validation

↓

Event Insert

↓

Inventory Update

↓

Commit
```

이를 통해 Race Condition을 방지한다.

---

# **49. Authentication and Household Sharing**

MVP 초기 개발에서는 단일 테스트 사용자로 시작할 수 있다.

실제 공유 기능을 구현할 때는 다음 구조를 사용한다.

```text
User

↓

Household Membership

↓

Household Data
```

모든 API는 로그인 사용자의 Household Membership을 검증한다.

---

## **49.1 household_members**

```text
id

household_id

user_id

role

joined_at
```

Role

```text
owner

member
```

MVP에서는 두 Role의 기능 차이를 최소화한다.

---

# **50. Environment Variables**

Backend 환경변수 예시

```text
APP_ENV

DATABASE_URL

OPENAI_API_KEY

STT_PROVIDER

LLM_PROVIDER

JWT_SECRET

AUDIO_STORAGE_PATH

MAX_AUDIO_DURATION_SECONDS

CORS_ALLOWED_ORIGINS
```

민감한 값은 Git에 포함하지 않는다.

`.env.example`에는 Key 이름만 제공한다.

---

# **51. Render Deployment**

Backend는 Render Web Service에 배포한다.

### **기본 실행 명령 예시**

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### **Health Check**

```text
GET /health
```

Response

```json
{
  "status": "ok"
}
```

### **Readiness Check**

```text
GET /ready
```

DB 연결 여부를 확인한다.

---

# **52. Neon Database**

Neon PostgreSQL을 Primary Database로 사용한다.

### **개발 원칙**

- Application은 Migration을 통해 Schema를 관리한다.
- 운영 DB에서 수동으로 컬럼을 추가하지 않는다.
- Connection Pool 사용을 고려한다.
- Transaction이 필요한 API는 단일 DB Session을 사용한다.
- 모든 Timestamp는 UTC로 저장한다.
- 클라이언트에서 사용자 시간대로 변환한다.

---

# **53. Database Migration**

Alembic을 사용한다.

```text
migrations/

versions/
```

초기 Migration 순서

```text
001_create_households_users

002_create_inventory_items

003_create_inventory_events

004_create_inventory_snapshot

005_create_voice_requests

006_create_action_plans

007_create_alias_and_unit_rules

008_create_audit_logs
```

---

# **54. Testing Strategy**

## **54.1 Backend Unit Test**

대상

- Action Plan Validation
- Unit Conversion
- Inventory 계산
- Negative Inventory Validation
- Event Reversal
- 목표 수량의 Adjustment 변환
- 품목 수정 및 Soft Delete Validation
- Idempotency
- 권한 검증

---

## **54.2 Backend Integration Test**

대상

- Voice Request 생성
- Action Plan 저장
- Execute Transaction
- 동시 실행
- Rollback
- Inventory 조회
- 품목 생성, 수정, 보관 및 복원
- 현재 수량 설정
- Event 정정 및 취소

---

## **54.3 Flutter Test**

대상

- Inventory 화면 렌더링
- Loading/Error/Empty 상태
- 품목 생성 및 수정
- 품목 보관 및 복원
- 현재 수량 설정
- 수동 입고 및 소비
- Event 정정 및 취소
- Action 수정
- Action 삭제
- 실행 버튼 상태
- API 오류 처리

---

## **54.4 Android Test**

대상

- Widget 클릭
- 녹음 Activity 실행
- 권한 거부
- 녹음 완료
- Flutter 화면 이동
- 백그라운드 복귀
- 프로세스 종료 후 재진입

---

# **55. Core Acceptance Test**

## **Test 1**

입력

```text
우유 두 개 사왔어.
```

기대 결과

```text
stock_in

우유

2개
```

사용자 승인 전에는 재고가 변경되지 않는다.

---

## **Test 2**

입력

```text
맥주 세 캔 마셨어.
```

기대 결과

```text
stock_out

맥주

3캔
```

---

## **Test 3**

입력

```text
콜라 한 박스 사왔고 우유 하나 마셨어.
```

기대 결과

두 개의 독립 Action이 생성된다.

---

## **Test 4**

입력

```text
맥주 좀 사왔어.
```

기대 결과

수량 미확인 상태로 실행이 차단된다.

---

## **Test 5**

현재 맥주 수량

```text
2캔
```

입력

```text
맥주 세 캔 마셨어.
```

기대 결과

음수 재고 Validation으로 실행이 차단된다.

---

## **Test 6**

사용자가 Action Plan에서 수량을 2에서 3으로 수정한다.

기대 결과

수정된 3개만 실행된다.

AI의 원본 수량 2개는 실행되지 않는다.

---

## **Test 7**

Execute 버튼을 연속으로 두 번 누른다.

기대 결과

Idempotency에 의해 Event는 한 번만 생성된다.

---

## **Test 8**

앱에서 현재 우유 수량을 5개에서 2개로 설정한다.

기대 결과

```text
adjustment_out 3개 Event 생성

현재 수량 2개
```

Inventory Snapshot을 직접 수정하지 않는다.

---

## **Test 9**

앱에서 잘못 생성된 `우유 +20` Event를 `우유 +2`로 정정한다.

기대 결과

```text
원본 +20 Event 보존

event_reversal -20 생성

대체 Event +2 생성

현재 수량 재계산
```

---

## **Test 10**

앱에서 수량 0인 품목을 보관한 후 복원한다.

기대 결과

```text
물리 삭제 없음

보관 시 is_active=false

복원 시 is_active=true
```

수량이 남은 품목의 보관은 차단된다.

---

# **56. MVP Implementation Order**

## **Phase 1. Backend 기본 구조**

- FastAPI 프로젝트 생성
- Neon 연결
- Migration 설정
- Inventory Item 생성, 조회, 수정, 보관 및 복원 구현
- Inventory Event 구현
- Inventory 조회 API 구현
- 수동 Event 생성 API 구현
- 현재 수량 설정 API 구현
- Event 정정 및 취소 API 구현

이 단계에서는 AI를 붙이지 않는다.

---

## **Phase 2. Flutter 기본 앱**

- Flutter 프로젝트 생성
- API Client 구현
- 재고 목록
- 품목 상세
- 기록 목록
- 품목 생성 및 정보 수정
- 품목 보관 및 복원
- 현재 수량 설정
- 수동 입고 및 소비
- Event 정정 및 취소
- 수동 새로고침
- 오류 상태

---

## **Phase 3. Action Plan**

- Voice Request 모델
- Action Plan 모델
- 임시 Transcript 입력 API
- LLM Action Plan 생성
- Action Plan 확인 화면
- Action 수정 및 삭제
- Execute API
- Item Alias 모델 및 검색
- 사용자가 품목 후보를 선택한 뒤 Alias 저장 여부 확인
- 승인된 음성 표현을 `voice_confirmation` Alias로 저장

초기에는 실제 음성 대신 텍스트 입력으로 검증한다.

---

## **Phase 4. 음성 처리**

- 앱 내부 녹음
- 음성 업로드
- STT 연결
- Transcript 확인
- Action Plan 생성 연결

---

## **Phase 5. Android Widget**

- Kotlin Widget 생성
- Widget Recording Activity
- Foreground Recording
- Flutter Deep Link
- Action Plan 화면 연결

---

## **Phase 6. 공유 기능**

- 사용자 인증
- Household
- Household Member
- 초대 또는 공유 방식
- 사용자별 Event 작성자 표시

---

# **57. MVP Definition of Done**

다음 조건을 모두 충족하면 MVP 완료로 본다.

- Android 홈 화면 Widget을 누르면 녹음 화면이 열린다.
- 사용자가 음성으로 입고 또는 소비 내용을 말할 수 있다.
- 음성이 Transcript로 변환된다.
- Transcript에서 하나 이상의 Action이 생성된다.
- 사용자가 Action을 확인할 수 있다.
- 사용자가 품목, 수량, 단위를 수정할 수 있다.
- 사용자가 특정 Action을 삭제할 수 있다.
- 앱에서 품목을 직접 생성하고 수정할 수 있다.
- 앱에서 품목을 보관하고 복원할 수 있다.
- 앱에서 현재 수량을 직접 설정할 수 있다.
- 앱에서 입고 및 소비 Event를 수동 생성할 수 있다.
- 앱에서 잘못된 Event를 정정하거나 취소할 수 있다.
- 수량 설정과 Event 정정 및 취소 후에도 원본 Event 이력이 보존된다.
- 승인 전에는 재고가 변경되지 않는다.
- 승인 후 Inventory Event가 생성된다.
- 현재 재고가 갱신된다.
- 기록 화면에서 변경 이력을 확인할 수 있다.
- 중복 실행이 방지된다.
- 음수 재고가 차단된다.
- 두 명의 사용자가 동일 Household 재고를 조회할 수 있다.

---

# **58. Out of Scope**

MVP에는 다음 기능을 포함하지 않는다.

- iOS
- 냉장고 사진 분석
- 영수증 OCR
- 바코드 인식
- 유통기한 자동 추론
- 레시피 추천
- 자동 장보기 주문
- 가격 비교
- 위치 기반 마트 추천
- 음성 상시 대기
- 스마트 스피커 연동
- 복잡한 식재료 중량 변환
- 소비 예측
- 월별 통계 대시보드

---

# **59. Future Roadmap**

## **v1.1**

- 자동 침묵 감지
- 잠금 화면 Shortcut
- 알림에서 수정 및 취소
- Action Plan 화면 음성 명령 모드
- 음성으로 Action 승인 및 전체 취소
- 음성으로 품목, 수량, 단위 수정
- 음성으로 특정 Action 삭제
- 자주 사용하는 품목 자동 추천
- 품목별 별칭 학습
- 단위 변환 규칙 관리
- Event 되돌리기

Action Plan 음성 명령은 앱이 사용자에게 보이고 음성 입력 상태가 명확히 표시된 동안만 수신한다.

예시:

```text
승인해

첫 번째 수량 3개로 바꿔

우유를 저지방 우유로 바꿔

두 번째 항목 삭제

전체 취소
```

음성 명령은 즉시 DB를 수정하지 않는다.

수정 명령은 Action Plan만 변경하고, 승인 명령이 최종적으로 인식되고 Backend 검증을 통과한 뒤 Execute한다.

TV 소리나 주변 대화에 의한 오작동을 줄이기 위해 다음을 TODO로 검증한다.

- Action Plan 진입 후 제한된 시간 동안만 명령 수신
- 화면에 Listening 상태 표시
- 명령 인식 결과를 화면과 음성으로 다시 안내
- 낮은 Confidence의 승인 및 삭제 명령 실행 차단
- `승인`, `취소`, `수정` 명령용 별도 Structured Command Schema
- 음성 승인 Execute의 Idempotency 적용

---

## **v1.2**

- 유통기한
- 부족 재고 알림
- 장보기 목록
- 주기적 구매 품목 감지
- 가족별 사용 기록

---

## **v2.0**

- 현재 재고 기반 레시피 추천
- 앱이 닫혀 있어도 동작하는 사용자 정의 호출어 연구
- `VoiceInteractionService` 및 기본 Assistant 역할 적용 가능성 검토
- On-device Wake Word Engine의 배터리, 개인정보, 기기 호환성 검증
- 호출어 이후 Action Plan 확인과 음성 승인까지 이어지는 완전 Hands-free Flow 연구

사용자 정의 호출어 예시:

```text
헤이 키퍼

우유 두 개 사 왔어
```

음성 상시 대기는 MVP 범위에 포함하지 않는다.

일반 앱의 백그라운드 마이크 접근 제한을 우회하는 방식으로 구현하지 않는다.

시스템이 허용하는 Assistant 역할, 사용자에게 명확히 보이는 Foreground 동작, 또는 사용자가 직접 시작한 세션 안에서만 구현한다.
- 식단 추천
- 소비량 분석
- 음식 폐기량 분석
- 냉장고 사진 인식
- 영수증 자동 입력

---

# **60. Long-Term Vision**

Voice Inventory Agent는 단순 재고관리 앱으로 제한하지 않는다.

장기적으로는 사용자의 가정생활 정보를 이해하고 필요한 행동을 보조하는 Household AI Agent로 확장한다.

첫 번째 Workflow는 다음과 같다.

```text
음성으로 재고 변경 기록
```

향후 Workflow 예시

```text
현재 재고 조회

부족 품목 확인

장보기 목록 작성

유통기한 확인

레시피 추천

소비 패턴 분석
```

그러나 장기 비전이 현재 MVP 범위를 확대해서는 안 된다.

첫 번째 목표는 다음 하나다.

사용자가 홈 화면에서 한 번 누르고 말한 뒤, 확인만 하면 재고가 정확하게 반영되는 경험을 완성한다.

---

# **61. Final Development Principles**

구현 과정에서는 다음 원칙을 항상 우선한다.

1. 사용자가 입력하는 단계를 최소화한다.
2. 승인 없이 재고를 변경하지 않는다.
3. AI 결과를 Backend에서 다시 검증한다.
4. LLM은 DB를 직접 수정하지 않는다.
5. 모든 재고 변경은 Event로 기록한다.
6. 기존 Event의 원본을 삭제하지 않는다.
7. Widget은 빠른 진입을 위한 수단이며 앱 전체를 대체하지 않는다.
8. Flutter는 화면과 사용자 상호작용을 담당한다.
9. Kotlin은 Android Widget과 녹음 진입을 담당한다.
10. FastAPI는 모든 비즈니스 규칙과 데이터 정합성을 책임진다.
11. PostgreSQL은 시스템의 최종 Source of Truth이다.
12. 구현 편의보다 기록 정확성과 복구 가능성을 우선한다.

---

# **62. AI Coding Assistant Instruction**

이 문서를 전달받은 AI Coding Assistant는 다음 원칙에 따라 작업한다.

- 본 문서를 프로젝트의 Source of Truth로 사용한다.
- 문서에 없는 기능을 임의로 추가하지 않는다.
- 한 번에 전체 시스템을 생성하지 않는다.
- Phase 단위로 구현한다.
- 각 Phase 시작 전 구현 범위를 요약한다.
- 기존 코드 구조를 확인한 후 수정한다.
- API와 DB 변경 시 Migration을 함께 작성한다.
- 테스트 없이 핵심 비즈니스 로직을 완료 처리하지 않는다.
- LLM 출력은 반드시 Schema Validation을 거친다.
- 승인 전 Inventory Event를 생성하지 않는다.
- 구현 중 문서와 충돌하는 결정이 필요하면 임의 결정하지 않고 별도 TODO로 기록한다.

최초 구현은 다음 Phase부터 시작한다.

```text
Phase 1

FastAPI 프로젝트 초기화

Neon PostgreSQL 연결

Alembic 설정

Inventory Item

Inventory Item 수정, 보관 및 복원

Inventory Event

Inventory 조회 API

수동 입출고 Event API

현재 수량 설정 API

Event 정정 및 취소 API

Backend 테스트
```

Phase 1이 완료되기 전에는 음성, LLM, Android Widget을 구현하지 않는다.



# **63. Phase 1 Implementation Specification**

## **63.1 Phase 1 목표**

Phase 1의 목표는 AI와 음성 기능 없이도 정상적으로 동작하는 재고관리 Backend를 완성하는 것이다.

이 단계에서 다음 흐름이 반드시 동작해야 한다.

```text
품목 생성

↓

품목 정보 수정 또는 보관 및 복원

↓

입고 또는 소비 Event 생성

↓

현재 재고 Snapshot 갱신

↓

현재 수량 직접 설정

↓

잘못된 Event 정정 또는 취소

↓

현재 재고 조회

↓

품목별 Event 이력 조회
```

Phase 1에서는 다음 기능을 구현하지 않는다.

- STT
- LLM
- Action Plan
- Flutter
- Android Widget
- 사용자 초대
- 음성 파일 업로드
- 외부 AI API 연동

---

# **64. Phase 1 Technology Decision**

## **64.1 Python**

Python 3.12 이상을 사용한다.

## **64.2 Package Manager**

`uv`를 기본 Package Manager로 사용한다.

프로젝트 초기화 예시:

```bash
uv init backend
cd backend
```

## **64.3 주요 Library**

```text
fastapi
uvicorn
sqlalchemy
asyncpg
alembic
pydantic
pydantic-settings
pytest
pytest-asyncio
httpx
```

개발용 Library:

```text
ruff
mypy
```

## **64.4 ORM**

SQLAlchemy 2.x Async 방식을 사용한다.

MVP에서는 SQLModel보다 SQLAlchemy와 Pydantic Schema를 분리하는 방식을 기본으로 한다.

선택 이유:

- DB 모델과 API Schema의 책임을 분리할 수 있다.
- 복잡한 Transaction과 Lock 처리에 적합하다.
- Alembic 연동이 명확하다.
- 향후 Event 및 Action Plan 구조 확장이 쉽다.

---

# **65. Phase 1 Project Structure**

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── inventory_items.py
│   │       ├── inventory.py
│   │       └── inventory_events.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── exceptions.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── household.py
│   │   ├── user.py
│   │   ├── household_member.py
│   │   ├── inventory_item.py
│   │   ├── inventory.py
│   │   ├── inventory_event.py
│   │   └── audit_log.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── inventory_item.py
│   │   ├── inventory.py
│   │   └── inventory_event.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── audit_log_repository.py
│   │   ├── inventory_item_repository.py
│   │   ├── inventory_repository.py
│   │   └── inventory_event_repository.py
│   │
│   └── services/
│       ├── __init__.py
│       ├── inventory_item_service.py
│       └── inventory_service.py
│
├── migrations/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
│
├── .env.example
├── alembic.ini
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

# **66. Phase 1 Database Schema**

## **66.1 households**

```sql
CREATE TABLE households (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## **66.2 users**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    nickname VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## **66.3 household_members**

```sql
CREATE TABLE household_members (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id),
    user_id UUID NOT NULL REFERENCES users(id),
    role VARCHAR(20) NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_household_member UNIQUE (household_id, user_id)
);
```

허용 Role:

```text
owner
member
```

Phase 1에서는 인증 기능을 구현하지 않는다.

개발용 기본 Household와 User를 Seed 데이터로 생성한다.

---

## **66.4 inventory_items**

```sql
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id),
    name VARCHAR(100) NOT NULL,
    normalized_name VARCHAR(100) NOT NULL,
    default_unit VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_inventory_item_name
        UNIQUE (household_id, normalized_name)
);
```

`normalized_name`은 검색 및 중복 방지를 위한 값이다.

예:

```text
원본: 코카콜라 제로
정규화: 코카콜라제로
```

Phase 1 정규화 규칙:

- 앞뒤 공백 제거
- 모든 공백 제거
- 영문 소문자 변환
- 특수문자 제거

---

## **66.5 inventory**

```sql
CREATE TABLE inventory (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id),
    item_id UUID NOT NULL REFERENCES inventory_items(id),
    quantity NUMERIC(12, 3) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_inventory_item UNIQUE (household_id, item_id),
    CONSTRAINT ck_inventory_quantity_nonnegative CHECK (quantity >= 0)
);
```

`inventory`는 현재 상태를 조회하기 위한 Snapshot 테이블이다.

---

## **66.6 inventory_events**

```sql
CREATE TABLE inventory_events (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id),
    item_id UUID NOT NULL REFERENCES inventory_items(id),
    event_type VARCHAR(30) NOT NULL,
    quantity NUMERIC(12, 3) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    signed_quantity NUMERIC(12, 3) NOT NULL,
    created_by UUID REFERENCES users(id),
    source VARCHAR(30) NOT NULL DEFAULT 'manual',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reversed_at TIMESTAMPTZ,
    reversed_by UUID REFERENCES users(id),
    reversal_event_id UUID REFERENCES inventory_events(id),
    CONSTRAINT ck_event_quantity_positive CHECK (quantity > 0)
);
```

허용 `event_type`:

```text
stock_in
stock_out
adjustment_in
adjustment_out
initial_stock
event_reversal
```

허용 `source`:

```text
manual
voice
system
correction
```

Phase 1에서는 기본값 `manual`을 사용한다.

---

## **66.7 audit_logs**

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    household_id UUID NOT NULL REFERENCES households(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    before_json JSONB,
    after_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Phase 1에서 기록할 `action`:

```text
inventory_item_created
inventory_item_updated
inventory_item_archived
inventory_item_restored
inventory_event_created
```

Audit Log 저장은 대상 품목 또는 Event 변경과 같은 Transaction에서 수행한다.

---

# **67. Signed Quantity Rule**

Event는 원래 수량과 계산용 수량을 함께 저장한다.

예:

```text
stock_in 2개

quantity = 2
signed_quantity = 2
```

```text
stock_out 2개

quantity = 2
signed_quantity = -2
```

변환 규칙:


| **Event Type** | **signed_quantity** |
| -------------- | ------------------- |
| stock_in       | `+quantity`         |
| adjustment_in  | `+quantity`         |
| initial_stock  | `+quantity`         |
| stock_out      | `-quantity`         |
| adjustment_out | `-quantity`         |
| event_reversal | 취소 대상 Event의 반대값    |


`signed_quantity` 값은 클라이언트가 전달하지 않는다.

Backend Service가 Event Type을 기준으로 계산한다.

---

# **68. Phase 1 API Specification**

## **68.1 Health Check**

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

---

## **68.2 Inventory Item 생성**

```http
POST /api/v1/inventory-items
```

Request:

```json
{
  "name": "우유",
  "default_unit": "개",
  "category": "drink"
}
```

Response:

```json
{
  "id": "uuid",
  "name": "우유",
  "default_unit": "개",
  "category": "drink",
  "is_active": true,
  "current_quantity": 0,
  "created_at": "2026-07-20T10:00:00Z"
}
```

처리 규칙:

- 동일 Household에서 정규화 이름이 같으면 `409 Conflict`
- 품목 생성과 동시에 `inventory` Snapshot Row를 수량 0으로 생성
- 두 작업은 하나의 Transaction으로 수행

---

## **68.3 Inventory Item 목록 조회**

```http
GET /api/v1/inventory-items
```

Query Parameter:

```text
search
category
include_inactive
limit
offset
```

기본값:

```text
include_inactive=false
limit=50
offset=0
```

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "우유",
      "default_unit": "개",
      "category": "drink",
      "is_active": true,
      "current_quantity": 2
    }
  ],
  "total": 1
}
```

---

## **68.4 Inventory Item 수정**

```http
PATCH /api/v1/inventory-items/{item_id}
```

Request:

```json
{
  "name": "저지방 우유",
  "default_unit": "개",
  "category": "drink"
}
```

처리 규칙:

- `name`, `default_unit`, `category` 중 하나 이상을 전달한다.
- 이름 변경 시 정규화 이름을 다시 계산하고 Household 내 중복을 검사한다.
- 기본 단위는 현재 수량이 0일 때만 변경할 수 있다.
- 기존 InventoryEvent의 이름과 단위는 변경하지 않는다.
- 비활성 품목의 정보도 수정할 수 있다.

Response:

```json
{
  "id": "uuid",
  "name": "저지방 우유",
  "default_unit": "개",
  "category": "drink",
  "is_active": true,
  "current_quantity": 0,
  "updated_at": "2026-07-20T10:00:00Z"
}
```

---

## **68.5 Inventory Item 보관**

```http
DELETE /api/v1/inventory-items/{item_id}
```

물리 삭제하지 않고 `is_active=false`로 변경한다.

처리 규칙:

- 현재 수량이 0인 품목만 보관할 수 있다.
- 수량이 남아 있으면 `409 Conflict`를 반환한다.
- 이미 보관된 품목에 같은 요청을 보내도 동일한 최종 상태를 반환한다.
- 보관된 품목의 기존 Event와 Snapshot은 유지한다.

Response는 `is_active=false`인 품목 정보를 반환한다.

---

## **68.6 Inventory Item 복원**

```http
POST /api/v1/inventory-items/{item_id}/restore
```

`is_active=true`로 변경하고 복원된 품목을 반환한다.

이미 활성 상태인 품목에 같은 요청을 보내도 동일한 최종 상태를 반환한다.

---

## **68.7 현재 재고 조회**

```http
GET /api/v1/inventory
```

Query Parameter:

```text
search
category
include_zero
sort
order
limit
offset
```

기본값:

```text
include_zero=true
sort=updated_at
order=desc
limit=50
offset=0
```

Response:

```json
{
  "items": [
    {
      "item_id": "uuid",
      "name": "우유",
      "quantity": 2,
      "unit": "개",
      "category": "drink",
      "is_active": true,
      "updated_at": "2026-07-20T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

## **68.8 품목 상세 조회**

```http
GET /api/v1/inventory/{item_id}
```

Response:

```json
{
  "item_id": "uuid",
  "name": "우유",
  "quantity": 2,
  "unit": "개",
  "category": "drink",
  "is_active": true,
  "updated_at": "2026-07-20T10:30:00Z",
  "recent_events": [
    {
      "id": "uuid",
      "event_type": "stock_in",
      "quantity": 3,
      "signed_quantity": 3,
      "unit": "개",
      "created_at": "2026-07-20T10:00:00Z"
    },
    {
      "id": "uuid",
      "event_type": "stock_out",
      "quantity": 1,
      "signed_quantity": -1,
      "unit": "개",
      "created_at": "2026-07-20T10:30:00Z"
    }
  ]
}
```

---

## **68.9 현재 수량 설정**

```http
PUT /api/v1/inventory/{item_id}/quantity
```

Request:

```json
{
  "quantity": 2,
  "unit": "개",
  "note": "실제 수량 확인"
}
```

`quantity`는 증감량이 아니라 사용자가 원하는 최종 수량이다.

처리 순서:

```text
Transaction 시작

↓

품목 및 Household 확인

↓

Inventory Row Lock

↓

단위 및 비활성 상태 검증

↓

delta = target_quantity - current_quantity

↓

delta > 0이면 adjustment_in 생성

delta < 0이면 adjustment_out 생성

delta = 0이면 Event를 생성하지 않음

↓

Inventory Snapshot 갱신

↓

Commit
```

Response:

```json
{
  "event_id": "uuid-or-null",
  "item_id": "uuid",
  "previous_quantity": 5,
  "current_quantity": 2,
  "changed": true,
  "created_at": "2026-07-20T10:00:00Z"
}
```

클라이언트는 `delta`, `event_type`, `signed_quantity`를 전달하지 않는다.

---

## **68.10 수동 Inventory Event 생성**

```http
POST /api/v1/inventory-events
```

Request:

```json
{
  "item_id": "uuid",
  "event_type": "stock_in",
  "quantity": 2,
  "unit": "개",
  "note": "초기 테스트"
}
```

Response:

```json
{
  "event_id": "uuid",
  "item_id": "uuid",
  "event_type": "stock_in",
  "quantity": 2,
  "signed_quantity": 2,
  "previous_quantity": 0,
  "current_quantity": 2,
  "created_at": "2026-07-20T10:00:00Z"
}
```

처리 순서:

```text
Transaction 시작

↓

품목 존재 및 Household 확인

↓

Inventory Row Lock

↓

단위 검증

↓

signed_quantity 계산

↓

음수 재고 검증

↓

Inventory Event 생성

↓

Inventory Snapshot 갱신

↓

Commit
```

---

## **68.11 Event 목록 조회**

```http
GET /api/v1/inventory-events
```

Query Parameter:

```text
item_id
event_type
source
from
to
limit
offset
```

Response:

```json
{
  "events": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "item_name": "우유",
      "event_type": "stock_in",
      "quantity": 2,
      "signed_quantity": 2,
      "unit": "개",
      "source": "manual",
      "note": null,
      "created_at": "2026-07-20T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## **68.12 Event 정정**

```http
PATCH /api/v1/inventory-events/{event_id}
```

Request:

```json
{
  "event_type": "stock_in",
  "quantity": 2,
  "unit": "개",
  "note": "20개가 아니라 2개"
}
```

처리 규칙:

- 원본 Event Row를 직접 수정하지 않는다.
- `event_reversal`과 대체 Event를 하나의 Transaction으로 생성한다.
- 원본 Event에 `reversed_at`, `reversed_by`, `reversal_event_id`를 기록한다.
- Inventory Row Lock, 단위 검증, 음수 재고 검증을 적용한다.
- 이미 취소된 Event와 `event_reversal`은 정정할 수 없다.
- 대체 Event의 `source`는 `correction`이다.

Response:

```json
{
  "original_event_id": "uuid",
  "reversal_event_id": "uuid",
  "replacement_event_id": "uuid",
  "previous_quantity": 20,
  "current_quantity": 2,
  "corrected_at": "2026-07-20T10:00:00Z"
}
```

---

## **68.13 Event 취소**

```http
DELETE /api/v1/inventory-events/{event_id}
```

원본 Event를 물리 삭제하지 않고 반대 수량의 `event_reversal`을 생성한다.

처리 규칙:

- Event 취소와 Snapshot 갱신은 하나의 Transaction이다.
- 이미 취소된 Event와 `event_reversal`은 취소할 수 없다.
- 취소 결과가 음수 재고가 되면 거부한다.
- 생성된 Event의 `source`는 `correction`이다.

Response:

```json
{
  "original_event_id": "uuid",
  "reversal_event_id": "uuid",
  "previous_quantity": 2,
  "current_quantity": 0,
  "cancelled_at": "2026-07-20T10:00:00Z"
}
```

---

# **69. Phase 1 Validation Rules**

## **69.1 품목 생성**

- 이름은 필수
- 이름은 1자 이상 100자 이하
- 기본 단위는 필수
- 동일 Household 내 중복 품목명 금지
- 이름의 앞뒤 공백 제거
- 빈 문자열 금지

품목 수정에도 동일한 이름 및 중복 검증을 적용한다.

추가 규칙:

- 기본 단위 변경은 현재 수량이 0일 때만 허용
- 품목 보관은 현재 수량이 0일 때만 허용
- 품목 삭제는 항상 Soft Delete로 처리

## **69.2 Event 생성**

- 존재하는 품목만 사용 가능
- 품목은 현재 Household 소속이어야 함
- 수량은 0보다 커야 함
- Event 단위는 품목 기본 단위와 같아야 함
- 허용되지 않은 Event Type 거부
- `stock_out`, `adjustment_out` 실행 후 수량이 0보다 작아지면 거부
- 비활성 품목에는 Event를 생성할 수 없음

## **69.3 수량 설정 및 Event 정정**

- 목표 수량은 0 이상이어야 함
- 수량 설정 단위는 품목 기본 단위와 같아야 함
- 목표 수량이 현재 수량과 같으면 Event를 생성하지 않음
- 비활성 품목의 수량은 설정할 수 없음
- 이미 취소된 Event는 다시 정정하거나 취소할 수 없음
- `event_reversal`은 정정하거나 취소할 수 없음
- 정정과 취소의 최종 수량이 음수이면 전체 작업을 거부
- 정정 대상 Event는 현재 Household 소속이어야 함

## **69.4 단위 정책**

Phase 1에서는 단위 변환을 구현하지 않는다.

Event의 단위는 반드시 품목의 `default_unit`과 같아야 한다.

예:

```text
우유 기본 단위 = 개
```

다음 요청은 허용한다.

```text
우유 2개 입고
```

다음 요청은 거부한다.

```text
우유 2박스 입고
```

단위 변환은 Phase 3에서 구현한다.

---

# **70. Phase 1 Error Response**

모든 오류는 다음 공통 형식을 사용한다.

```json
{
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "현재 재고보다 많은 수량을 소비할 수 없습니다.",
    "details": {
      "item_id": "uuid",
      "current_quantity": 2,
      "requested_quantity": 3
    }
  }
}
```

주요 Error Code:

```text
ITEM_NOT_FOUND
DUPLICATE_ITEM_NAME
INVALID_EVENT_TYPE
INVALID_QUANTITY
UNIT_MISMATCH
INSUFFICIENT_INVENTORY
INACTIVE_ITEM
ITEM_HAS_INVENTORY
UNIT_CHANGE_REQUIRES_ZERO_INVENTORY
EVENT_ALREADY_REVERSED
EVENT_NOT_CORRECTABLE
HOUSEHOLD_ACCESS_DENIED
DATABASE_ERROR
```

HTTP Status Code:


| **상황**        | **Status** |
| ------------- | ---------- |
| 잘못된 요청        | 400        |
| 인증 필요         | 401        |
| 권한 없음         | 403        |
| 품목 또는 Event 없음 | 404        |
| 중복, 남은 재고, 이미 취소된 Event | 409        |
| Validation 실패 | 422        |
| 서버 오류         | 500        |


---

# **71. Phase 1 Service Logic**

## **71.1 create_inventory_item**

```text
입력값 검증

↓

이름 정규화

↓

중복 품목 확인

↓

Inventory Item 생성

↓

수량 0 Inventory Snapshot 생성

↓

Commit
```

---

## **71.2 create_inventory_event**

```text
품목 조회

↓

Household 확인

↓

Inventory Snapshot Row Lock

↓

Event Type에 따라 signed_quantity 계산

↓

새 수량 계산

↓

음수 재고 검증

↓

Event 저장

↓

Snapshot 갱신

↓

Commit
```

새 수량 계산:

```text
new_quantity = current_quantity + signed_quantity
```

---

## **71.3 update_inventory_item**

```text
품목 및 Household 확인

↓

입력값과 정규화 이름 검증

↓

이름 변경 시 중복 확인

↓

기본 단위 변경 시 Inventory Row Lock 및 현재 수량 0 확인

↓

품목 정보 갱신

↓

Commit
```

---

## **71.4 archive_inventory_item**

```text
품목 및 Household 확인

↓

Inventory Row Lock

↓

현재 수량 0 확인

↓

is_active = false

↓

Commit
```

복원은 동일한 권한 확인 후 `is_active=true`로 변경한다.

---

## **71.5 set_inventory_quantity**

```text
품목 및 Household 확인

↓

Inventory Row Lock

↓

활성 상태, 단위, 목표 수량 검증

↓

현재 수량과 목표 수량의 차이 계산

↓

차이에 맞는 adjustment_in 또는 adjustment_out Event 저장

↓

Snapshot 갱신

↓

Commit
```

차이가 0이면 Event와 Snapshot을 변경하지 않는다.

---

## **71.6 correct_inventory_event**

```text
원본 Event와 Inventory Row Lock

↓

Household, 정정 가능 상태, 단위 검증

↓

원본 반대값의 event_reversal 저장

↓

대체 Event의 signed_quantity 계산

↓

최종 수량의 음수 여부 검증

↓

대체 Event 저장 및 원본에 취소 정보 기록

↓

Snapshot 갱신

↓

Commit
```

취소는 대체 Event 저장 단계를 제외한 동일한 흐름을 사용한다.

---

## **71.7 rebuild_inventory_snapshot**

Phase 1에서 관리용 Service 함수로 구현한다.

입력:

```text
household_id
item_id
```

처리:

```text
원본 Event와 event_reversal을 포함한 모든 Event의 signed_quantity 합계 계산

↓

Inventory Snapshot 갱신
```

취소된 원본 Event도 합계에서 제외하지 않는다.

원본과 그 반대값인 `event_reversal`이 함께 합산되어 상쇄되어야 한다.

이 함수는 Snapshot 불일치 복구 및 테스트에 사용한다.

MVP API로 외부 노출하지 않는다.

---

# **72. Phase 1 Seed Data**

개발 편의를 위해 다음 Seed 데이터를 제공한다.

Household:

```text
우리 집
```

User:

```text
테스트 사용자
```

Inventory Item:

```text
우유 / 개 / drink
계란 / 개 / food
제로콜라 / 캔 / drink
맥주 / 캔 / drink
참치캔 / 개 / food
```

초기 수량은 모두 0이다.

Seed는 별도 Script로 실행한다.

```bash
uv run python -m app.scripts.seed
```

Seed Script는 여러 번 실행해도 중복 데이터가 생성되지 않아야 한다.

---

# **73. Phase 1 Test Cases**

## **73.1 품목 생성 성공**

```text
우유 생성

↓

Inventory Item 생성

↓

Inventory Snapshot 수량 0 생성
```

## **73.2 품목명 중복**

```text
우유 생성

↓

다시 우유 생성

↓

409 Conflict
```

## **73.3 입고 성공**

```text
현재 우유 0

↓

stock_in 2

↓

현재 우유 2
```

## **73.4 소비 성공**

```text
현재 우유 2

↓

stock_out 1

↓

현재 우유 1
```

## **73.5 음수 재고 차단**

```text
현재 우유 1

↓

stock_out 2

↓

실행 실패

↓

현재 우유 1 유지
```

## **73.6 Transaction Rollback**

Event 저장 이후 Snapshot 갱신 과정에서 강제 오류 발생.

기대 결과:

```text
Event 저장 안 됨

Snapshot 변경 안 됨
```

## **73.7 Snapshot 재구축**

Event 합계와 Snapshot을 임의로 불일치시킨다.

`rebuild_inventory_snapshot` 실행 후 Event 합계와 일치해야 한다.

## **73.8 Household 권한**

다른 Household의 품목 ID로 Event 생성을 요청한다.

기대 결과:

```text
403 Forbidden
```

## **73.9 품목 수정 및 보관**

```text
품목명과 카테고리 수정 성공

현재 수량이 있는 품목의 기본 단위 변경 차단

현재 수량이 있는 품목의 보관 차단

수량 0 품목 보관 및 복원 성공
```

## **73.10 현재 수량 설정**

```text
현재 우유 5

↓

목표 수량 2로 설정

↓

adjustment_out 3 생성

↓

현재 우유 2
```

현재 수량과 목표 수량이 같으면 Event가 생성되지 않아야 한다.

## **73.11 Event 정정**

```text
기존 우유 stock_in 20

↓

stock_in 2로 정정

↓

event_reversal -20 및 대체 Event +2 생성

↓

원본 Event 보존

↓

현재 우유 2
```

두 Event와 Snapshot 갱신은 하나의 Transaction이어야 한다.

## **73.12 Event 취소**

```text
기존 우유 stock_in 2

↓

Event 취소

↓

event_reversal -2 생성

↓

원본 Event 보존

↓

현재 우유 0
```

이미 취소된 Event의 재취소와 `event_reversal` 취소는 차단해야 한다.

## **73.13 정정 Transaction Rollback**

Reversal 저장 이후 대체 Event 또는 Snapshot 갱신 과정에서 강제 오류를 발생시킨다.

기대 결과:

```text
Reversal Event 저장 안 됨

대체 Event 저장 안 됨

원본 Event의 reversed 필드 변경 안 됨

Snapshot 변경 안 됨
```

---

# **74. Phase 1 Completion Checklist**

다음 항목이 모두 완료되어야 Phase 1을 완료 처리한다.

- FastAPI 서버가 실행된다.
- `/health`가 정상 응답한다.
- Neon PostgreSQL에 연결된다.
- Alembic Migration이 정상 적용된다.
- 개발용 Seed를 생성할 수 있다.
- 품목을 생성할 수 있다.
- 중복 품목 생성이 차단된다.
- 품목 목록을 조회할 수 있다.
- 품목명과 카테고리를 수정할 수 있다.
- 수량 0 품목의 기본 단위를 수정할 수 있다.
- 품목을 Soft Delete 방식으로 보관하고 복원할 수 있다.
- 품목 생성, 수정, 보관 및 복원 Audit Log가 같은 Transaction에 저장된다.
- 이름 변경 History는 Alias로 자동 등록되지 않는다.
- 수량이 남은 품목의 기본 단위 변경과 보관이 차단된다.
- 현재 재고를 조회할 수 있다.
- 목표 수량을 직접 설정하면 Adjustment Event가 생성된다.
- 입고 Event를 생성할 수 있다.
- 소비 Event를 생성할 수 있다.
- Event를 정정하면 Reversal과 대체 Event가 생성된다.
- Event를 취소하면 Reversal Event가 생성된다.
- 정정 및 취소 후에도 원본 Event가 보존된다.
- 이미 취소된 Event의 중복 취소가 차단된다.
- 음수 재고가 차단된다.
- Event 목록을 조회할 수 있다.
- 품목 상세와 최근 Event를 조회할 수 있다.
- Event와 Snapshot이 하나의 Transaction으로 처리된다.
- Snapshot 재구축이 가능하다.
- Unit Test가 통과한다.
- Integration Test가 통과한다.
- README에 실행 방법이 작성된다.
- `.env.example`이 제공된다.
- Secret이 Repository에 포함되지 않는다.

---

# **75. Phase 1 Coding Assistant Start Prompt**

아래 지시를 기준으로 Phase 1 구현을 시작한다.

```text
이 저장소에서 Voice Inventory Agent의 Phase 1 Backend를 구현한다.

MASTER_SPEC.md의 63번부터 74번까지를 구현 기준으로 사용한다.

이번 작업 범위는 다음으로 제한한다.

- FastAPI 프로젝트 초기화
- SQLAlchemy 2.x Async 설정
- Neon PostgreSQL 연결
- Alembic Migration
- Household, User, HouseholdMember 모델
- InventoryItem 모델
- Inventory Snapshot 모델
- InventoryEvent 모델
- AuditLog 모델
- 개발용 Seed
- Inventory Item 생성 및 목록 API
- Inventory Item 수정, 보관 및 복원 API
- 품목 생성, 수정, 보관 및 복원 Audit Log
- 현재 재고 조회 API
- 품목 상세 조회 API
- 현재 수량 설정 API
- 수동 Inventory Event 생성 API
- Inventory Event 목록 API
- Inventory Event 정정 및 취소 API
- 음수 재고 방지
- Transaction 및 Row Lock
- Snapshot 재구축 Service
- Unit Test
- Integration Test
- README 및 .env.example

다음 기능은 구현하지 않는다.

- Flutter
- Android Widget
- 음성 녹음
- STT
- LLM
- Action Plan
- 사용자 초대 UI
- 단위 변환
- Event 물리 수정 및 삭제

먼저 현재 저장소 구조를 확인한다.

기존 코드가 없다면 문서의 프로젝트 구조에 맞게 초기화한다.

기존 코드가 있다면 구조를 유지하면서 문서의 책임 분리를 반영한다.

구현이 완료되면 다음 내용을 보고한다.

1. 구현된 기능
2. 생성 및 수정한 파일
3. 환경변수 설정 방법
4. Migration 실행 방법
5. Seed 실행 방법
6. 서버 실행 방법
7. 테스트 실행 방법
8. 테스트 결과
9. 남아 있는 TODO
10. Phase 2 진입 가능 여부
```
