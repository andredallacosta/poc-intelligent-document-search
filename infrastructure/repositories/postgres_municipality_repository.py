import logging
from typing import List, Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.municipality import Municipality
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.municipality_repository import MunicipalityRepository
from domain.value_objects.municipality_id import MunicipalityId
from infrastructure.database.models import MunicipalityModel

logger = logging.getLogger(__name__)


class PostgresMunicipalityRepository(MunicipalityRepository):
    """PostgreSQL implementation of Municipality repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, municipality: Municipality) -> Municipality:
        """Saves a municipality with upsert"""
        try:
            # Check if already exists
            existing = await self._session.get(MunicipalityModel, municipality.id.value)

            if existing:
                # Update existing
                existing.name = municipality.name
                existing.token_quota = municipality.token_quota
                existing.tokens_consumed = municipality.tokens_consumed
                existing.active = municipality.active
                existing.monthly_token_limit = municipality.monthly_token_limit
                existing.contract_date = municipality.contract_date
                existing.updated_at = municipality.updated_at
            else:
                # Create new
                model = MunicipalityModel(
                    id=municipality.id.value,
                    name=municipality.name,
                    token_quota=municipality.token_quota,
                    tokens_consumed=municipality.tokens_consumed,
                    active=municipality.active,
                    monthly_token_limit=municipality.monthly_token_limit,
                    contract_date=municipality.contract_date,
                    created_at=municipality.created_at,
                    updated_at=municipality.updated_at,
                )
                self._session.add(model)

            await self._session.flush()
            return municipality

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower():
                raise BusinessRuleViolationError(
                    f"Municipality with name '{municipality.name}' already exists"
                )
            raise BusinessRuleViolationError(f"Error saving municipality: {e}")

    async def find_by_id(
        self, municipality_id: MunicipalityId
    ) -> Optional[Municipality]:
        """Finds municipality by ID"""
        stmt = select(MunicipalityModel).where(
            MunicipalityModel.id == municipality_id.value
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_by_name(self, name: str) -> Optional[Municipality]:
        """Finds municipality by name"""
        stmt = select(MunicipalityModel).where(MunicipalityModel.name == name.strip())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_all_active(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Municipality]:
        """Lists all active municipalities"""
        stmt = select(MunicipalityModel).where(MunicipalityModel.active.is_(True))
        stmt = stmt.order_by(MunicipalityModel.name)

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Municipality]:
        """Lists all municipalities"""
        stmt = select(MunicipalityModel).order_by(MunicipalityModel.name)

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def update(self, municipality: Municipality) -> Municipality:
        """Updates a municipality"""
        return await self.save(municipality)

    async def delete(self, municipality_id: MunicipalityId) -> bool:
        """Removes a municipality"""
        try:
            stmt = delete(MunicipalityModel).where(
                MunicipalityModel.id == municipality_id.value
            )
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting municipality {municipality_id}: {e}")
            return False

    async def exists(self, municipality_id: MunicipalityId) -> bool:
        """Checks if municipality exists"""
        stmt = select(func.count(MunicipalityModel.id)).where(
            MunicipalityModel.id == municipality_id.value
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def exists_by_name(self, name: str) -> bool:
        """Checks if municipality exists by name"""
        stmt = select(func.count(MunicipalityModel.id)).where(
            MunicipalityModel.name == name.strip()
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def count(self) -> int:
        """Counts total municipalities"""
        stmt = select(func.count(MunicipalityModel.id))
        result = await self._session.execute(stmt)
        return result.scalar()

    async def count_active(self) -> int:
        """Counts active municipalities"""
        stmt = select(func.count(MunicipalityModel.id)).where(
            MunicipalityModel.active.is_(True)
        )
        result = await self._session.execute(stmt)
        return result.scalar()

    async def find_by_critical_quota(
        self, percentage_limit: float = 90.0
    ) -> List[Municipality]:
        """Finds municipalities with critical quota (near limit)"""
        stmt = (
            select(MunicipalityModel)
            .where(
                and_(
                    MunicipalityModel.active.is_(True),
                    MunicipalityModel.tokens_consumed
                    >= (MunicipalityModel.token_quota * percentage_limit / 100),
                    MunicipalityModel.tokens_consumed < MunicipalityModel.token_quota,
                )
            )
            .order_by(MunicipalityModel.name)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_by_exhausted_quota(self) -> List[Municipality]:
        """Finds municipalities with exhausted quota"""
        stmt = (
            select(MunicipalityModel)
            .where(
                and_(
                    MunicipalityModel.active.is_(True),
                    MunicipalityModel.tokens_consumed >= MunicipalityModel.token_quota,
                )
            )
            .order_by(MunicipalityModel.name)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    def _model_to_entity(self, model: MunicipalityModel) -> Municipality:
        """Converts model to entity"""
        return Municipality(
            id=MunicipalityId.from_uuid(model.id),
            name=model.name,
            token_quota=model.token_quota,
            tokens_consumed=model.tokens_consumed,
            active=model.active,
            monthly_token_limit=model.monthly_token_limit,
            contract_date=model.contract_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
