from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    action_plan_invalid_error,
    action_plan_provider_error,
    planner_not_configured_error,
    voice_request_not_found_error,
    voice_request_not_plannable_error,
)
from app.models import ActionPlan, VoiceRequest
from app.providers import (
    InventoryPlannerProvider,
    PlannerNotConfiguredError,
    PlannerProviderError,
)
from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.inventory_item_repository import (
    InventoryItemRepository,
    PlannerInventoryRecord,
)
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.action_plan import (
    ActionPlanPayload,
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
            signed_quantity = normalized_value if action.type == "stock_in" else -normalized_value
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
    ) -> None:
        self.voice_request_repository = voice_request_repository
        self.action_plan_repository = action_plan_repository
        self.inventory_item_repository = inventory_item_repository
        self.validator = validator

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
