"""Database repositories."""

from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.voice_request_repository import VoiceRequestRepository

__all__ = ["ActionPlanRepository", "VoiceRequestRepository"]
