from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class TokenStatusResponse(BaseModel):
    """Schema for token status response"""

    municipality_id: UUID
    municipality_active: bool
    status: str = Field(..., description="Status: active, suspended, unknown")
    base_limit: int = Field(..., ge=0, description="Base limit from plan")
    extra_credits: int = Field(..., ge=0, description="Extra credits purchased")
    total_limit: int = Field(..., ge=0, description="Total limit (base + extras)")
    consumed: int = Field(..., ge=0, description="Tokens already consumed")
    remaining: int = Field(..., ge=0, description="Tokens remaining")
    usage_percentage: float = Field(..., ge=0, le=100, description="Percentage used")
    period_start: Optional[str] = Field(None, description="Period start date (ISO)")
    period_end: Optional[str] = Field(None, description="Period end date (ISO)")
    days_remaining: int = Field(..., ge=0, description="Days until expiration")
    next_due_date: Optional[str] = Field(None, description="Next due date (ISO)")
    message: Optional[str] = Field(None, description="Additional message")

    class Config:
        json_schema_extra = {
            "example": {
                "municipality_id": "123e4567-e89b-12d3-a456-426614174000",
                "municipality_active": True,
                "status": "active",
                "base_limit": 20000,
                "extra_credits": 5000,
                "total_limit": 25000,
                "consumed": 12500,
                "remaining": 12500,
                "usage_percentage": 50.0,
                "period_start": "2024-01-05",
                "period_end": "2024-02-04",
                "days_remaining": 15,
                "next_due_date": "2024-02-05",
            }
        }


class AddCreditsRequest(BaseModel):
    """Schema for adding extra credits"""

    tokens: int = Field(..., gt=0, le=500000, description="Amount of tokens to add")
    reason: Optional[str] = Field(
        None, max_length=255, description="Reason for purchase"
    )

    @validator("tokens")
    def validate_tokens(cls, v):
        if v <= 0:
            raise ValueError("Tokens must be positive")
        if v > 500000:
            raise ValueError("Maximum 500k tokens per purchase")
        return v

    class Config:
        json_schema_extra = {
            "example": {"tokens": 10000, "reason": "Extra credits for campaign"}
        }


class UpdateLimitRequest(BaseModel):
    """Schema for updating monthly limit"""

    new_limit: int = Field(..., gt=0, le=1000000, description="New monthly limit")
    changed_by: Optional[str] = Field(
        None, max_length=255, description="Who made the change"
    )

    @validator("new_limit")
    def validate_new_limit(cls, v):
        if v <= 0:
            raise ValueError("Limit must be positive")
        if v > 1000000:
            raise ValueError("Limit cannot exceed 1M tokens")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "new_limit": 50000,
                "changed_by": "admin@municipality.gov.br",
            }
        }
