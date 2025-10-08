import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.token_usage_period import TokenUsagePeriod
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.token_usage_period_repository import TokenUsagePeriodRepository
from domain.value_objects.municipality_id import MunicipalityId
from infrastructure.database.models import TokenUsagePeriodModel

logger = logging.getLogger(__name__)


class PostgresTokenUsagePeriodRepository(TokenUsagePeriodRepository):
    """PostgreSQL implementation of token usage period repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, period: TokenUsagePeriod) -> TokenUsagePeriod:
        """Saves period with upsert to avoid duplicates"""
        try:
            # Check if already exists
            existing = await self._session.get(TokenUsagePeriodModel, period.id)

            if existing:
                # Update existing
                existing.base_limit = period.base_limit
                existing.extra_credits = period.extra_credits
                existing.tokens_consumed = period.tokens_consumed
                existing.updated_at = period.updated_at
            else:
                # Create new
                model = TokenUsagePeriodModel(
                    id=period.id,
                    municipality_id=period.municipality_id.value,
                    period_start=period.period_start,
                    period_end=period.period_end,
                    base_limit=period.base_limit,
                    extra_credits=period.extra_credits,
                    tokens_consumed=period.tokens_consumed,
                    created_at=period.created_at,
                    updated_at=period.updated_at,
                )
                self._session.add(model)

            await self._session.flush()
            return period

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                raise BusinessRuleViolationError(
                    "Period already exists for this municipality on this date"
                )
            raise BusinessRuleViolationError(f"Error saving period: {e}")

    async def find_by_id(self, period_id: UUID) -> Optional[TokenUsagePeriod]:
        """Finds period by ID"""
        model = await self._session.get(TokenUsagePeriodModel, period_id)
        return self._model_to_entity(model) if model else None

    async def find_current_period(
        self, municipality_id: MunicipalityId
    ) -> Optional[TokenUsagePeriod]:
        """Finds current period with optimized query"""
        stmt = (
            select(TokenUsagePeriodModel)
            .where(
                and_(
                    TokenUsagePeriodModel.municipality_id == municipality_id.value,
                    TokenUsagePeriodModel.period_start <= func.current_date(),
                    TokenUsagePeriodModel.period_end >= func.current_date(),
                )
            )
            .limit(1)
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def find_periods_by_municipality(
        self,
        municipality_id: MunicipalityId,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[TokenUsagePeriod]:
        """Finds periods with filters"""
        conditions = [TokenUsagePeriodModel.municipality_id == municipality_id.value]

        if start_date:
            conditions.append(TokenUsagePeriodModel.period_end >= start_date)

        if end_date:
            conditions.append(TokenUsagePeriodModel.period_start <= end_date)

        stmt = (
            select(TokenUsagePeriodModel)
            .where(and_(*conditions))
            .order_by(TokenUsagePeriodModel.period_start.desc())
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_expired_periods(
        self, limit: Optional[int] = None
    ) -> List[TokenUsagePeriod]:
        """Finds expired periods"""
        stmt = (
            select(TokenUsagePeriodModel)
            .where(TokenUsagePeriodModel.period_end < func.current_date())
            .order_by(TokenUsagePeriodModel.period_end.desc())
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def delete(self, period_id: UUID) -> bool:
        """Removes period (exceptional use)"""
        try:
            stmt = delete(TokenUsagePeriodModel).where(
                TokenUsagePeriodModel.id == period_id
            )
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting period {period_id}: {e}")
            return False

    def _model_to_entity(self, model: TokenUsagePeriodModel) -> TokenUsagePeriod:
        """Converts model to entity"""
        return TokenUsagePeriod(
            id=model.id,
            municipality_id=MunicipalityId(model.municipality_id),
            period_start=model.period_start,
            period_end=model.period_end,
            base_limit=model.base_limit,
            extra_credits=model.extra_credits,
            tokens_consumed=model.tokens_consumed,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
