from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import (
    ActionPlan,
    Inventory,
    InventoryEvent,
    InventoryItem,
    ItemAlias,
    VoiceRequest,
)
from app.providers import (
    InventoryPlannerProvider,
    PlannerProviderError,
    UnconfiguredInventoryPlannerProvider,
)
from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_event_repository import InventoryEventRepository
from app.repositories.inventory_item_repository import (
    InventoryItemRepository,
    PlannerInventoryRecord,
)
from app.repositories.inventory_repository import (
    CurrentInventoryRecord,
    InventoryRepository,
)
from app.repositories.item_alias_repository import ItemAliasRepository
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.action_plan import (
    ActionPlanActionUpdate,
    ActionPlanNewItemUpdate,
    ActionPlanPayload,
    PlannerInventoryItem,
)
from app.services.action_plan_service import ActionPlanService, ActionPlanValidator

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-000000000099")
REQUEST_ID = UUID("00000000-0000-4000-8000-000000000501")
PLAN_ID = UUID("00000000-0000-4000-8000-000000000601")
ITEM_ID = UUID("00000000-0000-4000-8000-000000000111")
CREATED_AT = datetime(2026, 7, 28, 13, 0, tzinfo=UTC)
USER_ID = UUID("00000000-0000-4000-8000-000000000222")


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeVoiceRequestRepository(VoiceRequestRepository):
    def __init__(self) -> None:
        self.request = VoiceRequest(
            id=REQUEST_ID,
            household_id=HOUSEHOLD_ID,
            transcript="우유 두 개 사왔어.",
            status="planning",
        )

    async def get_for_household(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
        for_update: bool = False,
    ) -> VoiceRequest | None:
        del session, for_update
        if request_id == REQUEST_ID and household_id == HOUSEHOLD_ID:
            return self.request
        return None

    async def save(
        self,
        session: AsyncSession,
        *,
        voice_request: VoiceRequest,
    ) -> None:
        del session, voice_request


class FakeActionPlanRepository(ActionPlanRepository):
    def __init__(self) -> None:
        self.plan: ActionPlan | None = None

    async def get_by_voice_request(
        self,
        session: AsyncSession,
        *,
        voice_request_id: UUID,
    ) -> ActionPlan | None:
        del session, voice_request_id
        return self.plan

    async def get_for_household(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
        for_update: bool = False,
    ) -> ActionPlan | None:
        del session, for_update
        if request_id == REQUEST_ID and household_id == HOUSEHOLD_ID:
            return self.plan
        return None

    async def add(
        self,
        session: AsyncSession,
        *,
        action_plan: ActionPlan,
    ) -> None:
        del session
        action_plan.id = PLAN_ID
        action_plan.created_at = CREATED_AT
        self.plan = action_plan

    async def save(
        self,
        session: AsyncSession,
        *,
        action_plan: ActionPlan,
    ) -> None:
        del session
        self.plan = action_plan


class FakeInventoryItemRepository(InventoryItemRepository):
    def __init__(self) -> None:
        self.created_items: list[InventoryItem] = []
        self.created_snapshots: list[Inventory] = []

    async def list_active_for_planner(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
    ) -> list[PlannerInventoryRecord]:
        del session, household_id
        return [
            PlannerInventoryRecord(
                item=InventoryItem(
                    id=ITEM_ID,
                    household_id=HOUSEHOLD_ID,
                    name="우유",
                    normalized_name="우유",
                    default_unit="개",
                    is_active=True,
                ),
                current_quantity=Decimal("1"),
            )
        ]

    async def normalized_name_exists(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_name: str,
        exclude_item_id: UUID | None = None,
    ) -> bool:
        del session, household_id, exclude_item_id
        return any(
            item.normalized_name == normalized_name for item in self.created_items
        )

    async def get_by_normalized_name(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_name: str,
    ) -> InventoryItem | None:
        del session, household_id
        return next(
            (
                item
                for item in self.created_items
                if item.normalized_name == normalized_name
            ),
            None,
        )

    async def add_with_snapshot(
        self,
        session: AsyncSession,
        *,
        item: InventoryItem,
        snapshot: Inventory,
    ) -> None:
        del session
        item.created_at = CREATED_AT
        item.updated_at = CREATED_AT
        self.created_items.append(item)
        self.created_snapshots.append(snapshot)


class FakeInventoryRepository(InventoryRepository):
    def __init__(self) -> None:
        self.record = CurrentInventoryRecord(
            snapshot=Inventory(
                household_id=HOUSEHOLD_ID,
                item_id=ITEM_ID,
                quantity=Decimal("1"),
            ),
            item=InventoryItem(
                id=ITEM_ID,
                household_id=HOUSEHOLD_ID,
                name="우유",
                normalized_name="우유",
                default_unit="개",
                is_active=True,
            ),
        )
        self.locked_item_ids: list[UUID] = []

    async def get_many_for_update(
        self,
        session: AsyncSession,
        *,
        item_ids: list[UUID],
    ) -> list[CurrentInventoryRecord]:
        del session
        self.locked_item_ids = item_ids
        return [self.record] if ITEM_ID in item_ids else []

    async def save_snapshot(
        self,
        session: AsyncSession,
        *,
        snapshot: Inventory,
    ) -> None:
        del session, snapshot


class FakeInventoryEventRepository(InventoryEventRepository):
    def __init__(self) -> None:
        self.events: list[InventoryEvent] = []

    async def add(
        self,
        session: AsyncSession,
        *,
        event: InventoryEvent,
    ) -> None:
        del session
        self.events.append(event)


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def add(self, session: AsyncSession, **kwargs: Any) -> None:
        del session
        self.actions.append(cast(str, kwargs["action"]))


class FakeItemAliasRepository(ItemAliasRepository):
    def __init__(self) -> None:
        self.aliases: list[ItemAlias] = []

    async def list_for_household(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
    ) -> dict[UUID, list[ItemAlias]]:
        del session, household_id
        grouped: dict[UUID, list[ItemAlias]] = {}
        for alias in self.aliases:
            grouped.setdefault(alias.inventory_item_id, []).append(alias)
        return grouped

    async def get_by_normalized_alias(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_alias: str,
    ) -> ItemAlias | None:
        del session, household_id
        return next(
            (
                alias
                for alias in self.aliases
                if alias.normalized_alias == normalized_alias
            ),
            None,
        )

    async def add(
        self,
        session: AsyncSession,
        *,
        alias: ItemAlias,
    ) -> None:
        del session
        alias.created_at = CREATED_AT
        self.aliases.append(alias)


class FakePlanner:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.calls = 0

    async def create_action_plan(
        self,
        *,
        transcript: str,
        inventory_context: list[PlannerInventoryItem],
    ) -> ActionPlanPayload:
        self.calls += 1
        if self.fails:
            raise PlannerProviderError
        return ActionPlanPayload.model_validate(
            {
                "version": "1.0",
                "transcript": transcript,
                "summary": "우유 2개 입고",
                "requires_confirmation": True,
                "actions": [
                    {
                        "action_id": "a1",
                        "type": "stock_in",
                        "item": {
                            "raw_name": "우유",
                            "matched_item_id": inventory_context[0].item_id,
                            "matched_name": inventory_context[0].name,
                            "is_new_item": False,
                        },
                        "quantity": {
                            "raw_value": 2,
                            "raw_unit": "개",
                            "normalized_value": 2,
                            "normalized_unit": "개",
                            "conversion_applied": False,
                            "conversion_reason": None,
                        },
                        "confidence": 0.98,
                        "warnings": [],
                        "requires_user_input": False,
                    }
                ],
            }
        )


class FakeNewItemPlanner:
    async def create_action_plan(
        self,
        *,
        transcript: str,
        inventory_context: list[PlannerInventoryItem],
    ) -> ActionPlanPayload:
        del inventory_context
        return ActionPlanPayload.model_validate(
            {
                "version": "1.0",
                "transcript": transcript,
                "summary": "아몬드 음료 2개 입고",
                "requires_confirmation": True,
                "actions": [
                    {
                        "action_id": "a1",
                        "type": "stock_in",
                        "item": {
                            "raw_name": "아몬드",
                            "matched_item_id": None,
                            "matched_name": None,
                            "is_new_item": True,
                            "new_item": None,
                        },
                        "quantity": {
                            "raw_value": 2,
                            "raw_unit": "개",
                            "normalized_value": None,
                            "normalized_unit": None,
                            "conversion_applied": False,
                            "conversion_reason": None,
                        },
                        "confidence": 0.6,
                        "warnings": [],
                        "requires_user_input": True,
                    }
                ],
            }
        )


def build_service(
    voice_repository: FakeVoiceRequestRepository,
    plan_repository: FakeActionPlanRepository,
) -> ActionPlanService:
    return ActionPlanService(
        voice_request_repository=voice_repository,
        action_plan_repository=plan_repository,
        inventory_item_repository=FakeInventoryItemRepository(),
        validator=ActionPlanValidator(),
        item_alias_repository=FakeItemAliasRepository(),
    )


async def test_generate_stores_plan_and_waits_for_confirmation() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    planner = FakePlanner()

    result = await build_service(voice_repository, plan_repository).generate(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, planner),
    )

    assert result.plan_id == PLAN_ID
    assert result.approved is False
    assert result.executed is False
    assert voice_repository.request.status == "waiting_confirmation"
    assert plan_repository.plan is not None
    assert planner.calls == 1


async def test_generate_returns_existing_plan_without_calling_provider_again() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    planner = FakePlanner()
    service = build_service(voice_repository, plan_repository)
    session = cast(AsyncSession, FakeSession())

    first = await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, planner),
    )
    second = await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, planner),
    )

    assert second.plan_id == first.plan_id
    assert planner.calls == 1


async def test_provider_failure_marks_request_failed_for_retry() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()

    with pytest.raises(AppError) as raised:
        await build_service(voice_repository, plan_repository).generate(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            request_id=REQUEST_ID,
            provider=cast(InventoryPlannerProvider, FakePlanner(fails=True)),
        )

    assert raised.value.code == "ACTION_PLAN_PROVIDER_ERROR"
    assert voice_repository.request.status == "failed"
    assert plan_repository.plan is None


async def test_missing_provider_configuration_returns_service_unavailable() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()

    with pytest.raises(AppError) as raised:
        await build_service(voice_repository, plan_repository).generate(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            request_id=REQUEST_ID,
            provider=UnconfiguredInventoryPlannerProvider(),
        )

    assert raised.value.code == "PLANNER_NOT_CONFIGURED"
    assert raised.value.status_code == 503
    assert voice_repository.request.status == "failed"


async def test_user_can_replace_action_with_set_quantity_zero() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    service = build_service(voice_repository, plan_repository)
    session = cast(AsyncSession, FakeSession())
    await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, FakePlanner()),
    )

    result = await service.update_action(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        action_id="a1",
        data=ActionPlanActionUpdate(
            type="set_quantity",
            item_id=ITEM_ID,
            quantity=0,
            unit="개",
        ),
    )

    action = result.payload.actions[0]
    assert action.type == "set_quantity"
    assert action.quantity.normalized_value == 0
    assert action.confidence == 1
    assert action.requires_user_input is False


async def test_last_action_cannot_be_deleted() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    service = build_service(voice_repository, plan_repository)
    session = cast(AsyncSession, FakeSession())
    await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, FakePlanner()),
    )

    with pytest.raises(AppError) as raised:
        await service.delete_action(
            session,
            household_id=HOUSEHOLD_ID,
            request_id=REQUEST_ID,
            action_id="a1",
        )

    assert raised.value.code == "ACTION_PLAN_REQUIRES_ACTION"


async def test_delete_removes_only_selected_action() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    service = build_service(voice_repository, plan_repository)
    session = cast(AsyncSession, FakeSession())
    await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, FakePlanner()),
    )
    assert plan_repository.plan is not None
    payload = ActionPlanPayload.model_validate(plan_repository.plan.payload_json)
    second = payload.actions[0].model_copy(
        update={"action_id": "a2", "type": "set_quantity"}
    )
    plan_repository.plan.payload_json = payload.model_copy(
        update={"actions": [payload.actions[0], second]}
    ).model_dump(mode="json")

    result = await service.delete_action(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        action_id="a1",
    )

    assert [action.action_id for action in result.payload.actions] == ["a2"]


async def test_execute_updates_snapshot_and_is_idempotent() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    inventory_repository = FakeInventoryRepository()
    event_repository = FakeInventoryEventRepository()
    audit_repository = FakeAuditLogRepository()
    service = ActionPlanService(
        voice_request_repository=voice_repository,
        action_plan_repository=plan_repository,
        inventory_item_repository=FakeInventoryItemRepository(),
        validator=ActionPlanValidator(),
        inventory_repository=inventory_repository,
        inventory_event_repository=event_repository,
        audit_log_repository=cast(AuditLogRepository, audit_repository),
        item_alias_repository=FakeItemAliasRepository(),
    )
    session = cast(AsyncSession, FakeSession())
    await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, FakePlanner()),
    )

    first = await service.execute(
        session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        request_id=REQUEST_ID,
    )
    second = await service.execute(
        session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        request_id=REQUEST_ID,
    )

    assert inventory_repository.locked_item_ids == [ITEM_ID]
    assert inventory_repository.record.snapshot.quantity == 3
    assert len(event_repository.events) == 1
    assert event_repository.events[0].event_type == "stock_in"
    assert event_repository.events[0].source == "voice"
    assert audit_repository.actions == [
        "inventory_event_created",
        "action_plan_approved",
    ]
    assert first.event_count == 1
    assert first.already_executed is False
    assert second.event_count == 0
    assert second.already_executed is True
    assert voice_repository.request.status == "completed"


async def test_confirmed_new_item_is_created_with_first_event_and_alias() -> None:
    voice_repository = FakeVoiceRequestRepository()
    plan_repository = FakeActionPlanRepository()
    item_repository = FakeInventoryItemRepository()
    inventory_repository = FakeInventoryRepository()
    event_repository = FakeInventoryEventRepository()
    audit_repository = FakeAuditLogRepository()
    alias_repository = FakeItemAliasRepository()
    service = ActionPlanService(
        voice_request_repository=voice_repository,
        action_plan_repository=plan_repository,
        inventory_item_repository=item_repository,
        validator=ActionPlanValidator(),
        inventory_repository=inventory_repository,
        inventory_event_repository=event_repository,
        audit_log_repository=cast(AuditLogRepository, audit_repository),
        item_alias_repository=alias_repository,
    )
    session = cast(AsyncSession, FakeSession())
    await service.generate(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        provider=cast(InventoryPlannerProvider, FakeNewItemPlanner()),
    )
    resolved = await service.resolve_new_item(
        session,
        household_id=HOUSEHOLD_ID,
        request_id=REQUEST_ID,
        action_id="a1",
        data=ActionPlanNewItemUpdate(
            type="stock_in",
            name="아몬드브리즈",
            default_unit="개",
            category="음료",
            quantity=2,
            remember_alias=True,
        ),
    )

    result = await service.execute(
        session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        request_id=REQUEST_ID,
    )

    assert resolved.payload.actions[0].item.new_item is not None
    assert len(item_repository.created_items) == 1
    assert item_repository.created_items[0].name == "아몬드브리즈"
    assert item_repository.created_snapshots[0].quantity == 2
    assert len(event_repository.events) == 1
    assert event_repository.events[0].item_id == item_repository.created_items[0].id
    assert event_repository.events[0].signed_quantity == 2
    assert [(alias.alias, alias.source) for alias in alias_repository.aliases] == [
        ("아몬드", "voice_confirmation")
    ]
    assert audit_repository.actions == [
        "inventory_item_created",
        "inventory_event_created",
        "action_plan_approved",
    ]
    assert result.event_count == 1


async def test_exact_confirmed_alias_resolves_before_candidate_inference() -> None:
    payload = await FakeNewItemPlanner().create_action_plan(
        transcript="아몬드 두 개 사왔어.",
        inventory_context=[],
    )
    item_repository = FakeInventoryItemRepository()
    inventory_records = await item_repository.list_active_for_planner(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
    )
    alias = ItemAlias(
        id=UUID("00000000-0000-4000-8000-000000000333"),
        household_id=HOUSEHOLD_ID,
        inventory_item_id=ITEM_ID,
        alias="아몬드",
        normalized_alias="아몬드",
        source="voice_confirmation",
    )

    matched = ActionPlanService._apply_exact_item_matches(
        payload=payload,
        inventory_records=inventory_records,
        aliases_by_item={ITEM_ID: [alias]},
    )

    action = matched.actions[0]
    assert action.item.matched_item_id == ITEM_ID
    assert action.item.matched_name == "우유"
    assert action.item.is_new_item is False
    assert action.quantity.normalized_value == 2
    assert action.requires_user_input is True
