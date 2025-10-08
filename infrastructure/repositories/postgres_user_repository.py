import logging
from typing import List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.user_repository import UserRepository
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole
from infrastructure.database.models import UserModel

logger = logging.getLogger(__name__)


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of User repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, user: User) -> User:
        """Saves a user"""
        try:
            model = UserModel(
                id=user.id.value,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                primary_municipality_id=(
                    user.primary_municipality_id.value if user.primary_municipality_id else None
                ),
                municipality_ids=[str(mid.value) for mid in user.municipality_ids],
                password_hash=user.password_hash,
                auth_provider=user.auth_provider.value,
                google_id=user.google_id,
                is_active=user.is_active,
                email_verified=user.email_verified,
                last_login=user.last_login,
                invitation_token=user.invitation_token,
                invitation_expires_at=user.invitation_expires_at,
                invited_by=user.invited_by.value if user.invited_by else None,
                created_at=user.created_at,
                updated_at=user.updated_at,
                # Compatibilidade com código existente
                name=user.full_name,
                municipality_id=(
                    user.primary_municipality_id.value if user.primary_municipality_id else None
                ),
                active=user.is_active,
            )

            self._session.add(model)
            await self._session.flush()

            return user

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower() and "email" in str(e).lower():
                raise BusinessRuleViolationError(
                    f"User with email '{user.email}' already exists"
                )
            raise BusinessRuleViolationError(f"Error saving user: {e}")

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Finds user by ID"""
        stmt = select(UserModel).where(UserModel.id == user_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_by_email(self, email: str) -> Optional[User]:
        """Finds user by email"""
        stmt = select(UserModel).where(UserModel.email == email.strip().lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_by_municipality_id(
        self,
        municipality_id: MunicipalityId,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[User]:
        """Finds users from a municipality"""
        # Busca por primary_municipality_id ou municipality_ids (array JSON)
        stmt = select(UserModel).where(
            (UserModel.primary_municipality_id == municipality_id.value) |
            (func.json_array_length(UserModel.municipality_ids) > 0) &
            (UserModel.municipality_ids.op('?')(str(municipality_id.value)))
        )
        stmt = stmt.order_by(UserModel.full_name)

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_all_active(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Lists all active users"""
        stmt = select(UserModel).where(UserModel.is_active.is_(True))
        stmt = stmt.order_by(UserModel.full_name)

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Lists all users"""
        stmt = select(UserModel).order_by(UserModel.name)

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_anonymous(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Lists anonymous users (without municipality)"""
        stmt = select(UserModel).where(UserModel.municipality_id.is_(None))
        stmt = stmt.order_by(UserModel.created_at.desc())

        if limit:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def update(self, user: User) -> User:
        """Updates a user"""
        try:
            stmt = (
                update(UserModel)
                .where(UserModel.id == user.id.value)
                .values(
                    email=user.email,
                    full_name=user.full_name,
                    role=user.role.value,
                    primary_municipality_id=(
                        user.primary_municipality_id.value if user.primary_municipality_id else None
                    ),
                    municipality_ids=[str(mid.value) for mid in user.municipality_ids],
                    password_hash=user.password_hash,
                    auth_provider=user.auth_provider.value,
                    google_id=user.google_id,
                    is_active=user.is_active,
                    email_verified=user.email_verified,
                    last_login=user.last_login,
                    invitation_token=user.invitation_token,
                    invitation_expires_at=user.invitation_expires_at,
                    invited_by=user.invited_by.value if user.invited_by else None,
                    updated_at=user.updated_at,
                    # Compatibilidade com código existente
                    name=user.full_name,
                    municipality_id=(
                        user.primary_municipality_id.value if user.primary_municipality_id else None
                    ),
                    active=user.is_active,
                )
            )

            result = await self._session.execute(stmt)

            if result.rowcount == 0:
                raise BusinessRuleViolationError(f"User {user.id} not found")

            return user

        except IntegrityError as e:
            await self._session.rollback()
            if "unique constraint" in str(e).lower() and "email" in str(e).lower():
                raise BusinessRuleViolationError(
                    f"User with email '{user.email}' already exists"
                )
            raise BusinessRuleViolationError(f"Error updating user: {e}")

    async def delete(self, user_id: UserId) -> bool:
        """Removes a user"""
        stmt = delete(UserModel).where(UserModel.id == user_id.value)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def exists(self, user_id: UserId) -> bool:
        """Checks if user exists"""
        stmt = select(func.count(UserModel.id)).where(UserModel.id == user_id.value)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def exists_by_email(self, email: str) -> bool:
        """Checks if user exists by email"""
        stmt = select(func.count(UserModel.id)).where(
            UserModel.email == email.strip().lower()
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def count(self) -> int:
        """Counts total users"""
        stmt = select(func.count(UserModel.id))
        result = await self._session.execute(stmt)
        return result.scalar()

    async def count_active(self) -> int:
        """Counts active users"""
        stmt = select(func.count(UserModel.id)).where(UserModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar()

    async def count_by_municipality(self, municipality_id: MunicipalityId) -> int:
        """Counts users from a municipality"""
        stmt = select(func.count(UserModel.id)).where(
            UserModel.municipality_id == municipality_id.value
        )
        result = await self._session.execute(stmt)
        return result.scalar()

    async def count_anonymous(self) -> int:
        """Counts anonymous users"""
        stmt = select(func.count(UserModel.id)).where(
            UserModel.municipality_id.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar()

    async def find_by_google_id(self, google_id: str) -> Optional[User]:
        """Finds user by Google ID"""
        stmt = select(UserModel).where(UserModel.google_id == google_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_by_invitation_token(self, token: str) -> Optional[User]:
        """Finds user by invitation token"""
        stmt = select(UserModel).where(UserModel.invitation_token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    def _model_to_entity(self, model: UserModel) -> User:
        """Converts model to entity"""
        # Converte municipality_ids de lista de strings para lista de MunicipalityId
        municipality_ids = []
        if model.municipality_ids:
            municipality_ids = [
                MunicipalityId.from_string(mid_str) 
                for mid_str in model.municipality_ids
            ]
        
        return User(
            id=UserId.from_uuid(model.id),
            email=model.email,
            full_name=model.full_name or model.name or "",  # Fallback para compatibilidade
            role=UserRole.from_string(model.role) if model.role else UserRole.USER,
            primary_municipality_id=(
                MunicipalityId.from_uuid(model.primary_municipality_id)
                if model.primary_municipality_id
                else (MunicipalityId.from_uuid(model.municipality_id) if model.municipality_id else None)
            ),
            municipality_ids=municipality_ids,
            password_hash=model.password_hash,
            auth_provider=AuthProvider.from_string(model.auth_provider) if model.auth_provider else AuthProvider.EMAIL_PASSWORD,
            google_id=model.google_id,
            is_active=model.is_active if model.is_active is not None else (model.active if model.active is not None else True),
            email_verified=model.email_verified if model.email_verified is not None else False,
            last_login=model.last_login,
            invitation_token=model.invitation_token,
            invitation_expires_at=model.invitation_expires_at,
            invited_by=UserId.from_uuid(model.invited_by) if model.invited_by else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
