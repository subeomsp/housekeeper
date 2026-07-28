from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    action_plan_action_not_found_error,
    action_plan_invalid_error,
    action_plan_not_editable_error,
    action_plan_not_found_error,
    action_plan_provider_error,
    action_plan_requires_action_error,
    planner_not_configured_error,
    unit_mismatch_error,
    voice_request_not_found_error,
    voice_request_not_plannable_error,
)
from app.models import ActionPlan, InventoryEvent, VoiceRequest
from app.providers import (
    InventoryPlannerProvider,
    PlannerNotConfiguredError,
    PlannerProviderError,
)
from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_event_repository import InventoryEventRepository
from app.repositories.inventory_item_repository import (
    InventoryItemRepository,
    PlannerInventoryRecord,
)
from app.repositories.inventory_repository import (
    InventoryRepository,
)
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.action_plan import (
    ActionPlanAction,
    ActionPlanActionUpdate,
    ActionPlanItemReference,
    ActionPlanPayload,
    ActionPlanQuantity,
    PlannerInventoryItem,
)
from app.services.inventory_item_service import normalize_item_name


@dataclass(frozen=True)
class ActionPlanView:
    request_id: UUID
    plan_id: UUID
    payload: ActionPlanPayload
    approved: bool
    executed: bool
    created_at: datetime


@dataclass(frozen=True)
class ActionPlanExecutionView:
    inventory_updated: bool
    event_count: int
    already_executed: bool


@dataclass(frozen=True)
class PlanValidationIssue:
    code: str
    message: str
    action_id: str | None = None

    def as_detail(self) -> dict[str, str]:
        detail = {"code": self.code, "message": self.message}
        if self.action_id is not None:
            detail["action_id"] = self.action_id
        return detail


class ActionPlanValidator:
    def validate(
        self,
        *,
        payload: ActionPlanPayload,
        transcript: str,
        inventory_records: list[PlannerInventoryRecord],
    ) -> list[PlanValidationIssue]:
        issues: list[PlanValidationIssue] = []
        if payload.transcript != transcript:
            issues.append(
                PlanValidationIssue(
                    code="TRANSCRIPT_MISMATCH",
                    message="Plan의 Transcript가 원본 요청과 일치하지 않습니다.",
                )
            )

        records_by_id = {record.item.id: record for record in inventory_records}
        running_quantities = {
            record.item.id: record.current_quantity for record in inventory_records
        }
        seen_targets: set[tuple[str, str]] = set()

        for action in payload.actions:
            item_reference = action.item
            quantity = action.quantity
            target_key = (
                str(item_reference.matched_item_id)
                if item_reference.matched_item_id is not None
                else normalize_item_name(item_reference.raw_name)
            )
            duplicate_key = (action.type, target_key)
            if duplicate_key in seen_targets:
                issues.append(
                    PlanValidationIssue(
                        code="DUPLICATE_ACTION",
                        message="같은 품목과 유형의 Action이 중복되었습니다.",
                        action_id=action.action_id,
                    )
                )
            seen_targets.add(duplicate_key)

            if quantity.conversion_applied:
                issues.append(
                    PlanValidationIssue(
                        code="UNIT_CONVERSION_UNVERIFIED",
                        message="서버에 등록되지 않은 단위 변환은 적용할 수 없습니다.",
                        action_id=action.action_id,
                    )
                )

            if action.confidence < 0.7 and not action.requires_user_input:
                issues.append(
                    PlanValidationIssue(
                        code="LOW_CONFIDENCE_REQUIRES_INPUT",
                        message="신뢰도가 낮은 Action은 사용자 수정이 필요합니다.",
                        action_id=action.action_id,
                    )
                )

            if item_reference.is_new_item:
                if not action.requires_user_input:
                    issues.append(
                        PlanValidationIssue(
                            code="NEW_ITEM_REQUIRES_INPUT",
                            message="신규 품목은 사용자의 확인이 필요합니다.",
                            action_id=action.action_id,
                        )
                    )
                continue

            item_id = item_reference.matched_item_id
            if item_id is None or item_id not in records_by_id:
                issues.append(
                    PlanValidationIssue(
                        code="MATCHED_ITEM_INVALID",
                        message="연결된 품목이 현재 Household의 활성 품목이 아닙니다.",
                        action_id=action.action_id,
                    )
                )
                continue

            record = records_by_id[item_id]
            if item_reference.matched_name != record.item.name:
                issues.append(
                    PlanValidationIssue(
                        code="MATCHED_NAME_MISMATCH",
                        message="연결된 품목명이 현재 공식 이름과 일치하지 않습니다.",
                        action_id=action.action_id,
                    )
                )

            if quantity.raw_unit != record.item.default_unit:
                if (
                    quantity.normalized_value is not None
                    or quantity.normalized_unit is not None
                    or not action.requires_user_input
                ):
                    issues.append(
                        PlanValidationIssue(
                            code="UNIT_REQUIRES_INPUT",
                            message=(
                                "기본 단위와 다른 표현은 변환 규칙 또는 사용자 확인이 필요합니다."
                            ),
                            action_id=action.action_id,
                        )
                    )
                continue

            if (
                quantity.normalized_value != quantity.raw_value
                or quantity.normalized_unit != record.item.default_unit
            ):
                issues.append(
                    PlanValidationIssue(
                        code="NORMALIZED_QUANTITY_INVALID",
                        message=(
                            "변환이 없는 수량은 원본 수량과 기본 단위가 그대로 유지되어야 합니다."
                        ),
                        action_id=action.action_id,
                    )
                )
                continue

            normalized_value = Decimal(str(quantity.normalized_value))
            if action.type == "set_quantity":
                next_quantity = normalized_value
            else:
                signed_quantity = (
                    normalized_value if action.type == "stock_in" else -normalized_value
                )
                next_quantity = running_quantities[item_id] + signed_quantity
            if next_quantity < Decimal("0"):
                issues.append(
                    PlanValidationIssue(
                        code="INSUFFICIENT_INVENTORY",
                        message="Action 순서대로 실행하면 재고가 음수가 됩니다.",
                        action_id=action.action_id,
                    )
                )
            else:
                running_quantities[item_id] = next_quantity

        return issues


class ActionPlanService:
    def __init__(
        self,
        *,
        voice_request_repository: VoiceRequestRepository,
        action_plan_repository: ActionPlanRepository,
        inventory_item_repository: InventoryItemRepository,
        validator: ActionPlanValidator,
        inventory_repository: InventoryRepository | None = None,
        inventory_event_repository: InventoryEventRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.voice_request_repository = voice_request_repository
        self.action_plan_repository = action_plan_repository
        self.inventory_item_repository = inventory_item_repository
        self.validator = validator
        self.inventory_repository = inventory_repository or InventoryRepository()
        self.inventory_event_repository = (
            inventory_event_repository or InventoryEventRepository()
        )
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    async def generate(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        request_id: UUID,
        provider: InventoryPlannerProvider,
    ) -> ActionPlanView:
        invalid_issues: list[PlanValidationIssue] = []
        created_view: ActionPlanView | None = None
        async with session.begin():
            voice_request = await self._get_request(
                session,
                request_id=request_id,
                household_id=household_id,
                for_update=True,
            )
            existing = await self.action_plan_repository.get_by_voice_request(
                session,
                voice_request_id=request_id,
            )
            if existing is not None:
                return self._to_view(existing)
            if voice_request.status not in {"planning", "failed"}:
                raise voice_request_not_plannable_error(
                    str(request_id),
                    voice_request.status,
                )
            if voice_request.transcript is None:
                raise voice_request_not_plannable_error(
                    str(request_id),
                    voice_request.status,
                )
            voice_request.status = "planning"
            await self.voice_request_repository.save(
                session,
                voice_request=voice_request,
            )
            inventory_records = await self.inventory_item_repository.list_active_for_planner(
                session,
                household_id=household_id,
            )
            transcript = voice_request.transcript

        inventory_context = [
            PlannerInventoryItem(
                item_id=record.item.id,
                name=record.item.name,
                default_unit=record.item.default_unit,
                current_quantity=record.current_quantity,
            )
            for record in inventory_records
        ]
        try:
            payload = await provider.create_action_plan(
                transcript=transcript,
                inventory_context=inventory_context,
            )
        except PlannerNotConfiguredError:
            await self._mark_failed(
                session,
                request_id=request_id,
                household_id=household_id,
            )
            raise planner_not_configured_error() from None
        except PlannerProviderError:
            await self._mark_failed(
                session,
                request_id=request_id,
                household_id=household_id,
            )
            raise action_plan_provider_error() from None

        async with session.begin():
            voice_request = await self._get_request(
                session,
                request_id=request_id,
                household_id=household_id,
                for_update=True,
            )
            existing = await self.action_plan_repository.get_by_voice_request(
                session,
                voice_request_id=request_id,
            )
            if existing is not None:
                return self._to_view(existing)
            current_inventory = await self.inventory_item_repository.list_active_for_planner(
                session,
                household_id=household_id,
            )
            issues = self.validator.validate(
                payload=payload,
                transcript=transcript,
                inventory_records=current_inventory,
            )
            if issues:
                voice_request.status = "failed"
                await self.voice_request_repository.save(
                    session,
                    voice_request=voice_request,
                )
                invalid_issues = issues
            else:
                action_plan = ActionPlan(
                    voice_request_id=request_id,
                    payload_json=payload.model_dump(mode="json"),
                    approved=False,
                    executed=False,
                )
                await self.action_plan_repository.add(
                    session,
                    action_plan=action_plan,
                )
                voice_request.status = "waiting_confirmation"
                await self.voice_request_repository.save(
                    session,
                    voice_request=voice_request,
                )
                created_view = self._to_view(action_plan)

        if invalid_issues:
            raise action_plan_invalid_error([issue.as_detail() for issue in invalid_issues])
        if created_view is None:
            raise RuntimeError("Action Plan 생성 결과가 없습니다.")
        return created_view

    async def get(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        request_id: UUID,
    ) -> ActionPlanView:
        async with session.begin():
            action_plan = await self._get_plan(
                session,
                request_id=request_id,
                household_id=household_id,
                for_update=False,
            )
            return self._to_view(action_plan)

    async def update_action(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        request_id: UUID,
        action_id: str,
        data: ActionPlanActionUpdate,
    ) -> ActionPlanView:
        async with session.begin():
            action_plan = await self._get_editable_plan(
                session,
                request_id=request_id,
                household_id=household_id,
            )
            inventory_records = await self.inventory_item_repository.list_active_for_planner(
                session,
                household_id=household_id,
            )
            record = next(
                (item for item in inventory_records if item.item.id == data.item_id),
                None,
            )
            if record is None:
                raise action_plan_invalid_error(
                    [
                        PlanValidationIssue(
                            code="MATCHED_ITEM_INVALID",
                            message=("선택한 품목이 현재 Household의 활성 품목이 아닙니다."),
                            action_id=action_id,
                        ).as_detail()
                    ]
                )
            if data.unit != record.item.default_unit:
                raise unit_mismatch_error(
                    str(data.item_id),
                    record.item.default_unit,
                    data.unit,
                )

            payload = ActionPlanPayload.model_validate(action_plan.payload_json)
            action_index = self._find_action_index(
                payload,
                request_id=request_id,
                action_id=action_id,
            )
            updated_action = ActionPlanAction(
                action_id=action_id,
                type=data.type,
                item=ActionPlanItemReference(
                    raw_name=record.item.name,
                    matched_item_id=record.item.id,
                    matched_name=record.item.name,
                    is_new_item=False,
                ),
                quantity=ActionPlanQuantity(
                    raw_value=data.quantity,
                    raw_unit=record.item.default_unit,
                    normalized_value=data.quantity,
                    normalized_unit=record.item.default_unit,
                    conversion_applied=False,
                    conversion_reason=None,
                ),
                confidence=1,
                warnings=[],
                requires_user_input=False,
            )
            actions = list(payload.actions)
            actions[action_index] = updated_action
            updated_payload = payload.model_copy(
                update={
                    "summary": f"사용자가 확인한 재고 변경 {len(actions)}건",
                    "actions": actions,
                }
            )
            self._validate_edited_payload(
                payload=updated_payload,
                inventory_records=inventory_records,
            )
            action_plan.payload_json = updated_payload.model_dump(mode="json")
            await self.action_plan_repository.save(
                session,
                action_plan=action_plan,
            )
            return self._to_view(action_plan)

    async def delete_action(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        request_id: UUID,
        action_id: str,
    ) -> ActionPlanView:
        async with session.begin():
            action_plan = await self._get_editable_plan(
                session,
                request_id=request_id,
                household_id=household_id,
            )
            payload = ActionPlanPayload.model_validate(action_plan.payload_json)
            action_index = self._find_action_index(
                payload,
                request_id=request_id,
                action_id=action_id,
            )
            if len(payload.actions) == 1:
                raise action_plan_requires_action_error(str(request_id))
            actions = list(payload.actions)
            actions.pop(action_index)
            updated_payload = payload.model_copy(
                update={
                    "summary": f"사용자가 확인한 재고 변경 {len(actions)}건",
                    "actions": actions,
                }
            )
            inventory_records = await self.inventory_item_repository.list_active_for_planner(
                session,
                household_id=household_id,
            )
            self._validate_edited_payload(
                payload=updated_payload,
                inventory_records=inventory_records,
            )
            action_plan.payload_json = updated_payload.model_dump(mode="json")
            await self.action_plan_repository.save(
                session,
                action_plan=action_plan,
            )
            return self._to_view(action_plan)

    async def execute(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        request_id: UUID,
    ) -> ActionPlanExecutionView:
        async with session.begin():
            # All mutation paths use the same lock order: request, plan, then
            # inventory snapshots sorted by item ID.
            voice_request = await self._get_request(
                session,
                request_id=request_id,
                household_id=household_id,
                for_update=True,
            )
            action_plan = await self._get_plan(
                session,
                request_id=request_id,
                household_id=household_id,
                for_update=True,
            )
            if action_plan.executed:
                return ActionPlanExecutionView(
                    inventory_updated=False,
                    event_count=0,
                    already_executed=True,
                )
            if voice_request.status != "waiting_confirmation" or action_plan.approved:
                raise action_plan_not_editable_error(str(request_id))

            payload = ActionPlanPayload.model_validate(action_plan.payload_json)
            unresolved_issues = self._execution_readiness_issues(payload)
            if unresolved_issues:
                raise action_plan_invalid_error(
                    [issue.as_detail() for issue in unresolved_issues]
                )

            item_ids = sorted(
                {
                    action.item.matched_item_id
                    for action in payload.actions
                    if action.item.matched_item_id is not None
                },
                key=str,
            )
            locked_records = await self.inventory_repository.get_many_for_update(
                session,
                item_ids=item_ids,
            )
            planner_records = [
                PlannerInventoryRecord(
                    item=record.item,
                    current_quantity=record.snapshot.quantity,
                )
                for record in locked_records
                if record.item.household_id == household_id and record.item.is_active
            ]
            issues = self.validator.validate(
                payload=payload,
                transcript=voice_request.transcript or "",
                inventory_records=planner_records,
            )
            if issues:
                raise action_plan_invalid_error(
                    [issue.as_detail() for issue in issues]
                )

            records_by_id = {record.item.id: record for record in locked_records}
            event_count = 0
            for action in payload.actions:
                item_id = action.item.matched_item_id
                normalized_value = action.quantity.normalized_value
                if item_id is None or normalized_value is None:
                    raise RuntimeError("검증된 Action에 실행 수량 또는 품목이 없습니다.")
                record = records_by_id[item_id]
                quantity = Decimal(str(normalized_value))
                event_type: str = action.type
                signed_quantity = quantity if event_type == "stock_in" else -quantity
                if event_type == "set_quantity":
                    signed_quantity = quantity - record.snapshot.quantity
                    if signed_quantity == 0:
                        continue
                    event_type = (
                        "adjustment_in" if signed_quantity > 0 else "adjustment_out"
                    )

                event = InventoryEvent(
                    id=uuid4(),
                    household_id=household_id,
                    item_id=item_id,
                    event_type=event_type,
                    quantity=abs(signed_quantity),
                    unit=record.item.default_unit,
                    signed_quantity=signed_quantity,
                    created_by=user_id,
                    source="voice",
                    note=None,
                )
                await self.inventory_event_repository.add(session, event=event)
                record.snapshot.quantity += signed_quantity
                await self.audit_log_repository.add(
                    session,
                    household_id=household_id,
                    user_id=user_id,
                    action="inventory_event_created",
                    target_type="inventory_event",
                    target_id=event.id,
                    before_json=None,
                    after_json={
                        "action_plan_id": str(action_plan.id),
                        "voice_request_id": str(request_id),
                        "action_id": action.action_id,
                        "item_id": str(item_id),
                        "event_type": event_type,
                        "quantity": str(event.quantity),
                        "signed_quantity": str(event.signed_quantity),
                        "unit": event.unit,
                        "source": event.source,
                    },
                )
                event_count += 1

            for record in locked_records:
                await self.inventory_repository.save_snapshot(
                    session,
                    snapshot=record.snapshot,
                )

            action_plan.approved = True
            action_plan.executed = True
            voice_request.status = "completed"
            await self.action_plan_repository.save(
                session,
                action_plan=action_plan,
            )
            await self.voice_request_repository.save(
                session,
                voice_request=voice_request,
            )
            await self.audit_log_repository.add(
                session,
                household_id=household_id,
                user_id=user_id,
                action="action_plan_approved",
                target_type="action_plan",
                target_id=action_plan.id,
                before_json={"approved": False, "executed": False},
                after_json={
                    "approved": True,
                    "executed": True,
                    "voice_request_id": str(request_id),
                    "event_count": event_count,
                },
            )

        return ActionPlanExecutionView(
            inventory_updated=event_count > 0,
            event_count=event_count,
            already_executed=False,
        )

    @staticmethod
    def _execution_readiness_issues(
        payload: ActionPlanPayload,
    ) -> list[PlanValidationIssue]:
        issues: list[PlanValidationIssue] = []
        for action in payload.actions:
            if (
                action.requires_user_input
                or action.item.is_new_item
                or action.item.matched_item_id is None
                or action.quantity.normalized_value is None
                or action.quantity.normalized_unit is None
            ):
                issues.append(
                    PlanValidationIssue(
                        code="ACTION_REQUIRES_INPUT",
                        message="사용자 확인이 끝나지 않은 Action은 실행할 수 없습니다.",
                        action_id=action.action_id,
                    )
                )
        return issues

    async def _get_request(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
        for_update: bool,
    ) -> VoiceRequest:
        voice_request = await self.voice_request_repository.get_for_household(
            session,
            request_id=request_id,
            household_id=household_id,
            for_update=for_update,
        )
        if voice_request is None:
            raise voice_request_not_found_error(str(request_id))
        return voice_request

    async def _get_plan(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
        for_update: bool,
    ) -> ActionPlan:
        action_plan = await self.action_plan_repository.get_for_household(
            session,
            request_id=request_id,
            household_id=household_id,
            for_update=for_update,
        )
        if action_plan is None:
            raise action_plan_not_found_error(str(request_id))
        return action_plan

    async def _get_editable_plan(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
    ) -> ActionPlan:
        # Keep the same lock order as generation and later execution:
        # VoiceRequest first, then ActionPlan, to avoid cross-flow deadlocks.
        voice_request = await self._get_request(
            session,
            request_id=request_id,
            household_id=household_id,
            for_update=True,
        )
        action_plan = await self._get_plan(
            session,
            request_id=request_id,
            household_id=household_id,
            for_update=True,
        )
        if (
            voice_request.status != "waiting_confirmation"
            or action_plan.approved
            or action_plan.executed
        ):
            raise action_plan_not_editable_error(str(action_plan.voice_request_id))
        return action_plan

    @staticmethod
    def _find_action_index(
        payload: ActionPlanPayload,
        *,
        request_id: UUID,
        action_id: str,
    ) -> int:
        for index, action in enumerate(payload.actions):
            if action.action_id == action_id:
                return index
        raise action_plan_action_not_found_error(str(request_id), action_id)

    def _validate_edited_payload(
        self,
        *,
        payload: ActionPlanPayload,
        inventory_records: list[PlannerInventoryRecord],
    ) -> None:
        issues = self.validator.validate(
            payload=payload,
            transcript=payload.transcript,
            inventory_records=inventory_records,
        )
        if issues:
            raise action_plan_invalid_error([issue.as_detail() for issue in issues])

    async def _mark_failed(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
    ) -> None:
        async with session.begin():
            voice_request = await self.voice_request_repository.get_for_household(
                session,
                request_id=request_id,
                household_id=household_id,
                for_update=True,
            )
            if voice_request is not None:
                existing = await self.action_plan_repository.get_by_voice_request(
                    session,
                    voice_request_id=request_id,
                )
                if existing is None:
                    voice_request.status = "failed"
                    await self.voice_request_repository.save(
                        session,
                        voice_request=voice_request,
                    )

    @staticmethod
    def _to_view(action_plan: ActionPlan) -> ActionPlanView:
        return ActionPlanView(
            request_id=action_plan.voice_request_id,
            plan_id=action_plan.id,
            payload=ActionPlanPayload.model_validate(action_plan.payload_json),
            approved=action_plan.approved,
            executed=action_plan.executed,
            created_at=action_plan.created_at,
        )


action_plan_service = ActionPlanService(
    voice_request_repository=VoiceRequestRepository(),
    action_plan_repository=ActionPlanRepository(),
    inventory_item_repository=InventoryItemRepository(),
    validator=ActionPlanValidator(),
)


def get_action_plan_service() -> ActionPlanService:
    return action_plan_service
