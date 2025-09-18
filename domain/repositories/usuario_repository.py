from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.usuario import Usuario
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.value_objects.usuario_id import UsuarioId


class UsuarioRepository(ABC):
    """Interface do repositório para Usuario"""

    @abstractmethod
    async def save(self, usuario: Usuario) -> Usuario:
        """Salva um usuário"""
        pass

    @abstractmethod
    async def find_by_id(self, usuario_id: UsuarioId) -> Optional[Usuario]:
        """Busca usuário por ID"""
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[Usuario]:
        """Busca usuário por email"""
        pass

    @abstractmethod
    async def find_by_prefeitura_id(
        self, prefeitura_id: PrefeituraId, limit: Optional[int] = None, offset: int = 0
    ) -> List[Usuario]:
        """Busca usuários de uma prefeitura"""
        pass

    @abstractmethod
    async def find_all_active(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Usuario]:
        """Lista todos os usuários ativos"""
        pass

    @abstractmethod
    async def find_all(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Usuario]:
        """Lista todos os usuários"""
        pass

    @abstractmethod
    async def find_anonimos(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Usuario]:
        """Lista usuários anônimos (sem prefeitura)"""
        pass

    @abstractmethod
    async def update(self, usuario: Usuario) -> Usuario:
        """Atualiza um usuário"""
        pass

    @abstractmethod
    async def delete(self, usuario_id: UsuarioId) -> bool:
        """Remove um usuário"""
        pass

    @abstractmethod
    async def exists(self, usuario_id: UsuarioId) -> bool:
        """Verifica se usuário existe"""
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Verifica se existe usuário com o email"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Conta total de usuários"""
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """Conta usuários ativos"""
        pass

    @abstractmethod
    async def count_by_prefeitura(self, prefeitura_id: PrefeituraId) -> int:
        """Conta usuários de uma prefeitura"""
        pass

    @abstractmethod
    async def count_anonimos(self) -> int:
        """Conta usuários anônimos"""
        pass
