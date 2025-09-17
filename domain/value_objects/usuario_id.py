from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Union


@dataclass(frozen=True)
class UsuarioId:
    """Value object para ID de Usuario"""
    
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("UsuarioId deve ser um UUID válido")
    
    @classmethod
    def generate(cls) -> 'UsuarioId':
        """Gera um novo ID único para Usuario"""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, id_str: str) -> 'UsuarioId':
        """Cria UsuarioId a partir de string"""
        try:
            return cls(UUID(id_str))
        except (ValueError, TypeError) as e:
            raise ValueError(f"String inválida para UsuarioId: {id_str}") from e
    
    @classmethod
    def from_uuid(cls, uuid_obj: UUID) -> 'UsuarioId':
        """Cria UsuarioId a partir de UUID"""
        return cls(uuid_obj)
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, UsuarioId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
