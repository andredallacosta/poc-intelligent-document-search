from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional
from uuid import UUID

from domain.entities.token_usage_period import TokenUsagePeriod
from domain.value_objects.municipality_id import MunicipalityId


class TokenUsagePeriodRepository(ABC):
    """Interface for token usage period repository"""

    @abstractmethod
    async def save(self, period: TokenUsagePeriod) -> TokenUsagePeriod:
        """Saves a usage period"""
        pass

    @abstractmethod
    async def find_by_id(self, period_id: UUID) -> Optional[TokenUsagePeriod]:
        """Finds period by ID"""
        pass

    @abstractmethod
    async def find_current_period(
        self, municipality_id: MunicipalityId
    ) -> Optional[TokenUsagePeriod]:
        """Finds current period for municipality (optimized)"""
        pass

    @abstractmethod
    async def find_periods_by_municipality(
        self,
        municipality_id: MunicipalityId,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[TokenUsagePeriod]:
        """Finds periods for a municipality with filters"""
        pass

    @abstractmethod
    async def find_expired_periods(
        self, limit: Optional[int] = None
    ) -> List[TokenUsagePeriod]:
        """Finds expired periods (for cleanup/reports)"""
        pass

    @abstractmethod
    async def delete(self, period_id: UUID) -> bool:
        """Removes a period (exceptional cases only)"""
        pass
