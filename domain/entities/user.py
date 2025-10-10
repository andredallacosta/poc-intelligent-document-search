import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from domain.value_objects.user_role import UserRole


@dataclass
class User:
    """User entity with authentication and multi-tenancy"""

    id: UserId = field(default_factory=lambda: UserId(uuid4()))
    email: str = ""
    full_name: str = ""
    role: UserRole = UserRole.USER
    primary_municipality_id: Optional[MunicipalityId] = None
    municipality_ids: List[MunicipalityId] = field(default_factory=list)

    # Autenticação
    password_hash: Optional[str] = None
    auth_provider: AuthProvider = AuthProvider.EMAIL_PASSWORD
    google_id: Optional[str] = None

    # Controle de conta
    is_active: bool = True
    email_verified: bool = False
    last_login: Optional[datetime] = None

    # Convite/Ativação
    invitation_token: Optional[str] = None
    invitation_expires_at: Optional[datetime] = None
    invited_by: Optional[UserId] = None

    # Auditoria
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Compatibilidade com código existente
    @property
    def name(self) -> str:
        """Compatibilidade com código existente"""
        return self.full_name

    @name.setter
    def name(self, value: str) -> None:
        """Compatibilidade com código existente"""
        self.full_name = value

    @property
    def municipality_id(self) -> Optional[MunicipalityId]:
        """Compatibilidade com código existente"""
        return self.primary_municipality_id

    @municipality_id.setter
    def municipality_id(self, value: Optional[MunicipalityId]) -> None:
        """Compatibilidade com código existente"""
        self.primary_municipality_id = value
        if value and value not in self.municipality_ids:
            self.municipality_ids.append(value)

    @property
    def active(self) -> bool:
        """Compatibilidade com código existente"""
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        """Compatibilidade com código existente"""
        self.is_active = value

    def __post_init__(self):
        self._validate_business_rules()

    def _validate_business_rules(self):
        """Validates user business rules"""
        # Email válido
        if not self.email or "@" not in self.email:
            raise BusinessRuleViolationError("Email inválido")

        if not self._is_valid_email(self.email):
            raise BusinessRuleViolationError("Email deve ter formato válido")

        if len(self.email) > 255:
            raise BusinessRuleViolationError(
                "Email não pode ter mais de 255 caracteres"
            )

        # Nome obrigatório
        if not self.full_name or len(self.full_name.strip()) < 2:
            raise BusinessRuleViolationError("Nome deve ter pelo menos 2 caracteres")

        if len(self.full_name) > 255:
            raise BusinessRuleViolationError("Nome não pode ter mais de 255 caracteres")

        # Validação por provider
        if self.auth_provider == AuthProvider.EMAIL_PASSWORD:
            if not self.password_hash:
                raise BusinessRuleViolationError(
                    "Password hash obrigatório para email/senha"
                )
        elif self.auth_provider == AuthProvider.GOOGLE_OAUTH2:
            if not self.google_id:
                raise BusinessRuleViolationError("Google ID obrigatório para OAuth2")

        # Prefeitura principal deve estar na lista
        if (
            self.primary_municipality_id
            and self.primary_municipality_id not in self.municipality_ids
        ):
            self.municipality_ids.append(self.primary_municipality_id)

        # Validação de roles e prefeituras
        if self.role == UserRole.USER and len(self.municipality_ids) > 1:
            raise BusinessRuleViolationError(
                "Usuários comuns só podem ter uma prefeitura"
            )

        # Convite válido
        if self.invitation_token and not self.invitation_expires_at:
            raise BusinessRuleViolationError(
                "Token de convite deve ter data de expiração"
            )

    def _is_valid_email(self, email: str) -> bool:
        """Validates email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email.strip()) is not None

    def can_access_municipality(self, municipality_id: MunicipalityId) -> bool:
        """Verifica se usuário pode acessar uma prefeitura"""
        return municipality_id in self.municipality_ids

    def can_manage_users(self) -> bool:
        """Verifica se pode gerenciar outros usuários"""
        return self.role.can_manage_users()

    def can_manage_municipality(self, municipality_id: MunicipalityId) -> bool:
        """Verifica se pode gerenciar uma prefeitura específica"""
        if self.role == UserRole.SUPERUSER:
            return True
        if self.role == UserRole.ADMIN:
            return municipality_id in self.municipality_ids
        return False

    def add_municipality(self, municipality_id: MunicipalityId) -> None:
        """Adiciona prefeitura ao usuário (apenas superuser/admin)"""
        if self.role == UserRole.USER:
            raise BusinessRuleViolationError(
                "Usuários comuns não podem ter múltiplas prefeituras"
            )

        if municipality_id not in self.municipality_ids:
            self.municipality_ids.append(municipality_id)
            self.updated_at = datetime.utcnow()

    def remove_municipality(self, municipality_id: MunicipalityId) -> None:
        """Remove prefeitura do usuário"""
        if municipality_id == self.primary_municipality_id:
            raise BusinessRuleViolationError(
                "Não é possível remover prefeitura principal"
            )

        if municipality_id in self.municipality_ids:
            self.municipality_ids.remove(municipality_id)
            self.updated_at = datetime.utcnow()

    def activate_account(
        self,
        password_hash: Optional[str] = None,
        auth_provider: Optional[AuthProvider] = None,
        google_id: Optional[str] = None,
    ) -> None:
        """Ativa conta após convite com escolha de método de autenticação"""
        if not self.invitation_token:
            raise BusinessRuleViolationError("Usuário não tem convite pendente")

        if (
            self.invitation_expires_at
            and datetime.utcnow() > self.invitation_expires_at
        ):
            raise BusinessRuleViolationError("Convite expirado")

        # Se auth_provider foi fornecido, atualiza (escolha do usuário na ativação)
        if auth_provider:
            self.auth_provider = auth_provider

        # Validações baseadas no auth_provider final
        if self.auth_provider == AuthProvider.EMAIL_PASSWORD:
            if not password_hash:
                raise BusinessRuleViolationError(
                    "Password obrigatório para ativação com email/senha"
                )
            self.password_hash = password_hash
            self.google_id = None  # Limpa google_id se existir
        elif self.auth_provider == AuthProvider.GOOGLE_OAUTH2:
            if not google_id:
                raise BusinessRuleViolationError(
                    "Google ID obrigatório para ativação com Google OAuth2"
                )
            self.google_id = google_id
            self.password_hash = None  # Limpa password_hash se existir

        self.is_active = True
        self.email_verified = True
        self.invitation_token = None
        self.invitation_expires_at = None
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Desativa usuário (soft delete)"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def update_last_login(self) -> None:
        """Atualiza timestamp do último login"""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    @classmethod
    def create_with_invitation(
        cls,
        email: str,
        full_name: str,
        role: UserRole,
        primary_municipality_id: MunicipalityId,
        invited_by: UserId,
        auth_provider: Optional[AuthProvider] = None,
        google_id: Optional[str] = None,
    ) -> "User":
        """Factory method para criar usuário com convite (auth_provider será definido na ativação)"""
        import secrets
        from datetime import timedelta

        invitation_token = secrets.token_urlsafe(32)
        invitation_expires = datetime.utcnow() + timedelta(days=7)

        # Usuário "neutro" - auth_provider será definido na ativação
        # Usamos EMAIL_PASSWORD como padrão temporário, mas será sobrescrito
        final_auth_provider = auth_provider or AuthProvider.EMAIL_PASSWORD

        # Hash temporário que será substituído na ativação
        password_hash = "temp_hash_to_be_replaced_on_activation"

        return cls(
            email=email,
            full_name=full_name,
            role=role,
            primary_municipality_id=primary_municipality_id,
            municipality_ids=[primary_municipality_id],
            auth_provider=final_auth_provider,
            google_id=google_id,
            password_hash=password_hash,
            is_active=False,
            email_verified=False,
            invitation_token=invitation_token,
            invitation_expires_at=invitation_expires,
            invited_by=invited_by,
        )

    @classmethod
    def create(
        cls,
        name: str,
        email: str,
        municipality_id: Optional[MunicipalityId] = None,
        active: bool = True,
    ) -> "User":
        """Factory method to create new User (compatibilidade)"""
        municipality_ids = [municipality_id] if municipality_id else []

        return cls(
            id=UserId.generate(),
            full_name=name.strip(),
            email=email.strip().lower(),
            primary_municipality_id=municipality_id,
            municipality_ids=municipality_ids,
            is_active=active,
        )

    @classmethod
    def create_anonymous(cls, name: str = "Anonymous User") -> "User":
        """Creates anonymous user (without municipality)"""
        anonymous_email = f"anonymous+{UserId.generate()}@temp.local"
        return cls.create(
            name=name, email=anonymous_email, municipality_id=None, active=True
        )

    def link_municipality(self, municipality_id: MunicipalityId) -> None:
        """Links user to a municipality"""
        if not isinstance(municipality_id, MunicipalityId):
            raise BusinessRuleViolationError(
                "Municipality ID must be a valid MunicipalityId"
            )

        self.municipality_id = municipality_id
        self.updated_at = datetime.utcnow()

    def unlink_municipality(self) -> None:
        """Removes municipality link (makes anonymous)"""
        self.municipality_id = None
        self.updated_at = datetime.utcnow()

    def update_email(self, new_email: str) -> None:
        """Updates user email"""
        new_email = new_email.strip().lower()

        if not self._is_valid_email(new_email):
            raise BusinessRuleViolationError("New email must have valid format")

        if len(new_email) > 255:
            raise BusinessRuleViolationError("New email cannot exceed 255 characters")

        self.email = new_email
        self.updated_at = datetime.utcnow()

    def update_name(self, new_name: str) -> None:
        """Updates user name"""
        new_name = new_name.strip()

        if not new_name:
            raise BusinessRuleViolationError("New name is required")

        if len(new_name) > 255:
            raise BusinessRuleViolationError("New name cannot exceed 255 characters")

        self.name = new_name
        self.updated_at = datetime.utcnow()

    def set_password(self, password_hash: str) -> None:
        """Sets user password hash"""
        if not password_hash or len(password_hash.strip()) == 0:
            raise BusinessRuleViolationError("Password hash is required")

        self.password_hash = password_hash.strip()
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activates user"""
        self.active = True
        self.updated_at = datetime.utcnow()

    @property
    def is_anonymous(self) -> bool:
        """Checks if user is anonymous (without municipality)"""
        return self.municipality_id is None

    @property
    def has_municipality(self) -> bool:
        """Checks if user is linked to a municipality"""
        return self.municipality_id is not None

    @property
    def has_authentication(self) -> bool:
        """Checks if user has password configured"""
        return self.password_hash is not None and len(self.password_hash) > 0

    @property
    def email_domain(self) -> str:
        """Extracts email domain"""
        return self.email.split("@")[1] if "@" in self.email else ""
