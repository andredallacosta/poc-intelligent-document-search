from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.user import User
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId


class UserRepository(ABC):
    """Repository interface for User"""

    @abstractmethod
    async def save(self, user: User) -> User:
        """Saves a user"""
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Finds user by ID"""
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Finds user by email"""
        pass

    @abstractmethod
    async def find_by_municipality_id(
        self,
        municipality_id: MunicipalityId,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[User]:
        """Finds users from a municipality"""
        pass

    @abstractmethod
    async def find_all_active(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Lists all active users"""
        pass

    @abstractmethod
    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Lists all users"""
        pass

    @abstractmethod
    async def find_anonymous(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Lists anonymous users (without municipality)"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Updates a user"""
        pass

    @abstractmethod
    async def delete(self, user_id: UserId) -> bool:
        """Removes a user"""
        pass

    @abstractmethod
    async def exists(self, user_id: UserId) -> bool:
        """Checks if user exists"""
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Checks if user exists by email"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Counts total users"""
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """Counts active users"""
        pass

    @abstractmethod
    async def count_by_municipality(self, municipality_id: MunicipalityId) -> int:
        """Counts users from a municipality"""
        pass

    @abstractmethod
    async def count_anonymous(self) -> int:
        """Counts anonymous users"""
        pass

    @abstractmethod
    async def find_by_google_id(self, google_id: str) -> Optional[User]:
        """Finds user by Google ID"""
        pass

    @abstractmethod
    async def find_by_invitation_token(self, token: str) -> Optional[User]:
        """Finds user by invitation token"""
        pass
