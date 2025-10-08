from dataclasses import dataclass
from typing import Optional

from domain.value_objects.municipality_id import MunicipalityId


@dataclass
class TokenStatusDTO:
    """DTO for token status"""

    municipality_active: bool
    status: str
    base_limit: int
    extra_credits: int
    total_limit: int
    consumed: int
    remaining: int
    usage_percentage: float
    period_start: Optional[str]
    period_end: Optional[str]
    days_remaining: int
    next_due_date: Optional[str]
    message: Optional[str] = None


@dataclass
class AddCreditsRequestDTO:
    """DTO for adding credits"""

    municipality_id: MunicipalityId
    tokens: int
    reason: Optional[str] = None


@dataclass
class UpdateLimitRequestDTO:
    """DTO for updating limit"""

    municipality_id: MunicipalityId
    new_limit: int
    changed_by: Optional[str] = None
