from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.municipality import Municipality
from domain.value_objects.municipality_id import MunicipalityId


class MunicipalityRepository(ABC):
    """Repository interface for Municipality"""

    @abstractmethod
    async def save(self, municipality: Municipality) -> Municipality:
        """Saves a municipality"""
        pass

    @abstractmethod
    async def find_by_id(
        self, municipality_id: MunicipalityId
    ) -> Optional[Municipality]:
        """Finds municipality by ID"""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Municipality]:
        """Finds municipality by name"""
        pass

    @abstractmethod
    async def find_all_active(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Municipality]:
        """Lists all active municipalities"""
        pass

    @abstractmethod
    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Municipality]:
        """Lists all municipalities"""
        pass

    @abstractmethod
    async def update(self, municipality: Municipality) -> Municipality:
        """Updates a municipality"""
        pass

    @abstractmethod
    async def delete(self, municipality_id: MunicipalityId) -> bool:
        """Removes a municipality"""
        pass

    @abstractmethod
    async def exists(self, municipality_id: MunicipalityId) -> bool:
        """Checks if municipality exists"""
        pass

    @abstractmethod
    async def exists_by_name(self, name: str) -> bool:
        """Checks if municipality exists by name"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Counts total municipalities"""
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """Counts active municipalities"""
        pass

    @abstractmethod
    async def find_by_critical_quota(
        self, percentage_limit: float = 90.0
    ) -> List[Municipality]:
        """Finds municipalities with critical quota (near limit)"""
        pass

    @abstractmethod
    async def find_by_exhausted_quota(self) -> List[Municipality]:
        """Finds municipalities with exhausted quota"""
        pass
