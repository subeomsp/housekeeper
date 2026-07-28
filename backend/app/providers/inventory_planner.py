import json
from pathlib import Path
from typing import Annotated, Protocol

from fastapi import Depends
from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings, get_settings
from app.schemas.action_plan import ActionPlanPayload, PlannerInventoryItem

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "inventory_planner.txt"


class PlannerProviderError(Exception):
    """Raised when an external Planner cannot return a validated result."""


class PlannerNotConfiguredError(PlannerProviderError):
    """Raised when no usable Planner credentials are configured."""


class InventoryPlannerProvider(Protocol):
    async def create_action_plan(
        self,
        *,
        transcript: str,
        inventory_context: list[PlannerInventoryItem],
    ) -> ActionPlanPayload: ...


class OpenAIInventoryPlannerProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    async def create_action_plan(
        self,
        *,
        transcript: str,
        inventory_context: list[PlannerInventoryItem],
    ) -> ActionPlanPayload:
        context_json = json.dumps(
            [item.model_dump(mode="json") for item in inventory_context],
            ensure_ascii=False,
        )
        try:
            response = await self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Transcript:\n{transcript}\n\n현재 활성 재고 품목:\n{context_json}"
                        ),
                    },
                ],
                text_format=ActionPlanPayload,
            )
        except OpenAIError as exception:
            raise PlannerProviderError from exception

        if response.output_parsed is None:
            raise PlannerProviderError
        return response.output_parsed


class UnconfiguredInventoryPlannerProvider:
    async def create_action_plan(
        self,
        *,
        transcript: str,
        inventory_context: list[PlannerInventoryItem],
    ) -> ActionPlanPayload:
        del transcript, inventory_context
        raise PlannerNotConfiguredError("Planner Provider is not configured.")


def get_inventory_planner_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> InventoryPlannerProvider:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIInventoryPlannerProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    return UnconfiguredInventoryPlannerProvider()
