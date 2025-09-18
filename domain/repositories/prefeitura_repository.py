from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.prefeitura import Prefeitura
from domain.value_objects.prefeitura_id import PrefeituraId


class PrefeituraRepository(ABC):
    """Interface do repositório para Prefeitura"""

    @abstractmethod
    async def save(self, prefeitura: Prefeitura) -> Prefeitura:
        """Salva uma prefeitura"""
        pass

    @abstractmethod
    async def find_by_id(self, prefeitura_id: PrefeituraId) -> Optional[Prefeitura]:
        """Busca prefeitura por ID"""
        pass

    @abstractmethod
    async def find_by_nome(self, nome: str) -> Optional[Prefeitura]:
        """Busca prefeitura por nome"""
        pass

    @abstractmethod
    async def find_all_active(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Prefeitura]:
        """Lista todas as prefeituras ativas"""
        pass

    @abstractmethod
    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Prefeitura]:
        """Lista todas as prefeituras"""
        pass

    @abstractmethod
    async def update(self, prefeitura: Prefeitura) -> Prefeitura:
        """Atualiza uma prefeitura"""
        pass

    @abstractmethod
    async def delete(self, prefeitura_id: PrefeituraId) -> bool:
        """Remove uma prefeitura"""
        pass

    @abstractmethod
    async def exists(self, prefeitura_id: PrefeituraId) -> bool:
        """Verifica se prefeitura existe"""
        pass

    @abstractmethod
    async def exists_by_nome(self, nome: str) -> bool:
        """Verifica se existe prefeitura com o nome"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Conta total de prefeituras"""
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """Conta prefeituras ativas"""
        pass

    @abstractmethod
    async def find_by_quota_critica(
        self, percentual_limite: float = 90.0
    ) -> List[Prefeitura]:
        """Busca prefeituras com quota crítica (próxima do limite)"""
        pass

    @abstractmethod
    async def find_by_quota_esgotada(self) -> List[Prefeitura]:
        """Busca prefeituras com quota esgotada"""
        pass
