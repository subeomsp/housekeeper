from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

VoiceRequestStatus = Literal[
    "recording",
    "uploading",
    "transcribing",
    "planning",
    "waiting_confirmation",
    "executing",
    "completed",
    "failed",
]


class TextVoiceRequestCreate(BaseModel):
    transcript: str = Field(min_length=1)

    @field_validator("transcript")
    @classmethod
    def strip_transcript(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Transcript는 빈 문자열일 수 없습니다.")
        return stripped


class TextVoiceRequestResponse(BaseModel):
    request_id: UUID
    transcript: str
    status: VoiceRequestStatus
    created_at: datetime
