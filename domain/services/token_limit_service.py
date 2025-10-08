import logging
from datetime import date, timedelta
from typing import Optional

from domain.entities.municipality import Municipality
from domain.entities.token_usage_period import TokenUsagePeriod
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.exceptions.token_exceptions import (
    MunicipalityInactiveError,
    TokenLimitExceededError,
)
from domain.repositories.municipality_repository import MunicipalityRepository
from domain.repositories.token_usage_period_repository import TokenUsagePeriodRepository
from domain.value_objects.municipality_id import MunicipalityId
from infrastructure.services.token_lock_service import TokenLockService

logger = logging.getLogger(__name__)


class TokenLimitService:
    """Domain service for token limit control"""

    def __init__(
        self,
        municipality_repo: MunicipalityRepository,
        period_repo: TokenUsagePeriodRepository,
        lock_service: TokenLockService,
    ):
        self._municipality_repo = municipality_repo
        self._period_repo = period_repo
        self._lock_service = lock_service

    async def has_available_tokens(
        self, municipality_id: MunicipalityId, tokens_needed: int = 1
    ) -> bool:
        """Checks if municipality has available tokens"""
        try:
            municipality = await self._municipality_repo.find_by_id(municipality_id)
            if not municipality:
                return False

            if not municipality.active:
                return False

            period = await self._get_or_create_current_period(municipality)
            return period.remaining_tokens >= tokens_needed

        except Exception as e:
            logger.error(f"Error checking available tokens: {e}")
            return False

    async def consume_tokens_atomically(
        self,
        municipality_id: MunicipalityId,
        tokens_consumed: int,
        metadata: Optional[dict] = None,
    ) -> TokenUsagePeriod:
        """Consumes tokens atomically with distributed lock"""
        return await self._lock_service.with_period_lock(
            municipality_id,
            self._do_consume_tokens,
            municipality_id,
            tokens_consumed,
            metadata,
        )

    async def _do_consume_tokens(
        self,
        municipality_id: MunicipalityId,
        tokens_consumed: int,
        metadata: Optional[dict] = None,
    ) -> TokenUsagePeriod:
        """Internal implementation of token consumption (executed with lock)"""
        if tokens_consumed <= 0:
            raise BusinessRuleViolationError("Token amount must be positive")

        # 1. Find municipality and validate if active
        municipality = await self._municipality_repo.find_by_id(municipality_id)
        if not municipality:
            raise BusinessRuleViolationError("Municipality not found")

        if not municipality.active:
            raise MunicipalityInactiveError("Municipality with overdue payment")

        # 2. Find or create current period
        period = await self._get_or_create_current_period(municipality)

        # 3. Check if has sufficient tokens
        if period.remaining_tokens < tokens_consumed:
            raise TokenLimitExceededError(
                f"Insufficient tokens. Available: {period.remaining_tokens}, "
                f"Requested: {tokens_consumed}"
            )

        # 4. Consume tokens
        period.consume_tokens(tokens_consumed)

        # 5. Save updated period
        await self._period_repo.save(period)

        # 6. Structured log for audit
        logger.info(
            "token_consumption",
            extra={
                "municipality_id": str(municipality_id.value),
                "tokens_consumed": tokens_consumed,
                "tokens_remaining": period.remaining_tokens,
                "limit_total": period.total_limit,
                "usage_percentage": period.usage_percentage,
                "period_id": str(period.id),
                "metadata": metadata or {},
            },
        )

        return period

    async def _get_or_create_current_period(
        self, municipality: Municipality
    ) -> TokenUsagePeriod:
        """Finds current period or creates new if needed (lazy renewal)"""
        # 1. Try to find current period
        current_period = await self._period_repo.find_current_period(municipality.id)

        # 2. If exists and not expired, return it
        if current_period and not current_period.is_expired:
            return current_period

        # 3. If doesn't exist or expired, create new (only if municipality active)
        if not municipality.can_renew_period():
            raise MunicipalityInactiveError("Inactive municipality cannot renew period")

        return await self._create_new_period(municipality)

    async def _create_new_period(self, municipality: Municipality) -> TokenUsagePeriod:
        """Creates new period based on contract date"""
        today = date.today()

        # Calculate period start and end based on contract date
        start, end = self._calculate_period_dates(municipality.contract_date, today)

        # Create new period
        new_period = TokenUsagePeriod.create_new_period(municipality, start, end)

        # Save to database
        await self._period_repo.save(new_period)

        logger.info(
            "new_period_created",
            extra={
                "municipality_id": str(municipality.id.value),
                "period_id": str(new_period.id),
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "limit_base": new_period.base_limit,
            },
        )

        return new_period

    def _calculate_period_dates(
        self, contract_date: date, reference: date
    ) -> tuple[date, date]:
        """Calculates period start and end dates based on contract"""
        contract_day = contract_date.day

        # If we haven't reached the due date this month
        if reference.day < contract_day:
            # Current period: last month to this month
            if reference.month == 1:
                start = date(reference.year - 1, 12, contract_day)
            else:
                try:
                    start = date(reference.year, reference.month - 1, contract_day)
                except ValueError:
                    # Day doesn't exist in previous month
                    start = date(reference.year, reference.month - 1, 28)

            try:
                end = date(reference.year, reference.month, contract_day) - timedelta(
                    days=1
                )
            except ValueError:
                end = date(reference.year, reference.month, 28) - timedelta(days=1)
        else:
            # Current period: this month to next month
            try:
                start = date(reference.year, reference.month, contract_day)
            except ValueError:
                start = date(reference.year, reference.month, 28)

            if reference.month == 12:
                try:
                    end = date(reference.year + 1, 1, contract_day) - timedelta(days=1)
                except ValueError:
                    end = date(reference.year + 1, 1, 28) - timedelta(days=1)
            else:
                try:
                    end = date(
                        reference.year, reference.month + 1, contract_day
                    ) - timedelta(days=1)
                except ValueError:
                    end = date(reference.year, reference.month + 1, 28) - timedelta(
                        days=1
                    )

        return start, end

    async def add_extra_credits(
        self,
        municipality_id: MunicipalityId,
        tokens: int,
        reason: str = "Extra credits purchase",
    ) -> TokenUsagePeriod:
        """Adds extra credits to current period"""
        return await self._lock_service.with_period_lock(
            municipality_id, self._do_add_extra_credits, municipality_id, tokens, reason
        )

    async def _do_add_extra_credits(
        self, municipality_id: MunicipalityId, tokens: int, reason: str
    ) -> TokenUsagePeriod:
        """Internal implementation of adding credits"""
        municipality = await self._municipality_repo.find_by_id(municipality_id)
        if not municipality:
            raise BusinessRuleViolationError("Municipality not found")

        period = await self._get_or_create_current_period(municipality)
        period.add_credits(tokens, reason)

        await self._period_repo.save(period)

        logger.info(
            "extra_credits_added",
            extra={
                "municipality_id": str(municipality_id.value),
                "tokens_added": tokens,
                "new_limit_total": period.total_limit,
                "reason": reason,
            },
        )

        return period

    async def update_monthly_limit(
        self,
        municipality_id: MunicipalityId,
        new_limit: int,
        changed_by: str = "system",
    ) -> tuple[Municipality, Optional[TokenUsagePeriod]]:
        """Updates municipality monthly limit (affects current period)"""
        return await self._lock_service.with_period_lock(
            municipality_id,
            self._do_update_monthly_limit,
            municipality_id,
            new_limit,
            changed_by,
        )

    async def _do_update_monthly_limit(
        self, municipality_id: MunicipalityId, new_limit: int, changed_by: str
    ) -> tuple[Municipality, Optional[TokenUsagePeriod]]:
        """Internal implementation of limit update"""
        municipality = await self._municipality_repo.find_by_id(municipality_id)
        if not municipality:
            raise BusinessRuleViolationError("Municipality not found")

        old_limit = municipality.monthly_token_limit

        # Update municipality limit
        municipality.update_monthly_limit(new_limit)
        await self._municipality_repo.save(municipality)

        # Update current period if exists
        current_period = await self._period_repo.find_current_period(municipality_id)
        if current_period:
            current_period.base_limit = new_limit
            await self._period_repo.save(current_period)

        logger.info(
            "monthly_limit_updated",
            extra={
                "municipality_id": str(municipality_id.value),
                "old_limit": old_limit,
                "new_limit": new_limit,
                "changed_by": changed_by,
                "period_updated": current_period is not None,
            },
        )

        return municipality, current_period

    async def get_token_status(self, municipality_id: MunicipalityId) -> dict:
        """Returns complete token status for municipality"""
        try:
            municipality = await self._municipality_repo.find_by_id(municipality_id)
            if not municipality:
                return {"error": "Municipality not found"}

            if not municipality.active:
                return {
                    "municipality_active": False,
                    "status": "suspended",
                    "message": "Municipality with overdue payment",
                    "total_limit": 0,
                    "remaining": 0,
                }

            period = await self._get_or_create_current_period(municipality)

            return {
                "municipality_active": True,
                "status": "active",
                "base_limit": period.base_limit,
                "extra_credits": period.extra_credits,
                "total_limit": period.total_limit,
                "consumed": period.tokens_consumed,
                "remaining": period.remaining_tokens,
                "usage_percentage": period.usage_percentage,
                "period_start": period.period_start.isoformat(),
                "period_end": period.period_end.isoformat(),
                "days_remaining": period.days_remaining,
                "next_due_date": municipality.calculate_next_due_date().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting token status: {e}")
            return {"error": "Internal server error"}
