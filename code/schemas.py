from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TicketStatus(StrEnum):
    REPLIED = "replied"
    ESCALATED = "escalated"


class RequestType(StrEnum):
    PRODUCT_ISSUE = "product_issue"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    INVALID = "invalid"


class RunTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    ticket_id: str = Field(min_length=1)
    company: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    data_root: Path

    @field_validator("data_root")
    @classmethod
    def validate_data_root(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        if not resolved.exists():
            raise ValueError(f"data_root does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"data_root is not a directory: {resolved}")
        return resolved


@dataclass(frozen=True)
class TicketDeps:
    data_root: Path
    ticket_id: str
    company: str

    @classmethod
    def from_request(cls, request: RunTicketRequest) -> TicketDeps:
        return cls(
            data_root=request.data_root,
            ticket_id=request.ticket_id,
            company=request.company,
        )


class TicketResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: TicketStatus
    product_area: str = Field(default="")
    response: str = Field(min_length=1)
    justification: str = Field(min_length=1)
    request_type: RequestType

    @field_validator("product_area", "response", "justification")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()

    @field_validator("response", "justification")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_product_area(self) -> TicketResult:
        if self.product_area:
            return self
        if self.request_type == RequestType.INVALID or self.status == TicketStatus.ESCALATED:
            return self
        raise ValueError(
            "product_area must not be blank for non-invalid, non-escalated results"
        )
