from enum import Enum


class UserRole(Enum):
    """Roles hierárquicos do sistema"""
    SUPERUSER = "superuser"  # Equipe interna - acesso total
    ADMIN = "admin"          # Chefe da prefeitura - gerencia usuários
    USER = "user"            # Funcionário - usa IA

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "UserRole":
        """Cria UserRole a partir de string"""
        for role in cls:
            if role.value == value.lower():
                return role
        raise ValueError(f"Invalid user role: {value}")

    def can_manage_users(self) -> bool:
        """Verifica se pode gerenciar outros usuários"""
        return self in [UserRole.SUPERUSER, UserRole.ADMIN]

    def can_access_all_municipalities(self) -> bool:
        """Verifica se pode acessar todas as prefeituras"""
        return self == UserRole.SUPERUSER

    def is_admin_or_higher(self) -> bool:
        """Verifica se é admin ou superior"""
        return self in [UserRole.SUPERUSER, UserRole.ADMIN]
