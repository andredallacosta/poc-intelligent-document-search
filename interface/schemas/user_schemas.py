from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateUserRequest(BaseModel):
    """Schema para criação de usuário"""

    email: EmailStr = Field(description="Email do usuário")
    full_name: str = Field(min_length=2, max_length=255, description="Nome completo")
    role: str = Field(description="Role do usuário: user, admin, superuser")
    primary_municipality_id: UUID = Field(description="ID da prefeitura principal")
    municipality_ids: Optional[List[UUID]] = Field(
        default=None, description="IDs das prefeituras adicionais (opcional)"
    )
    auth_provider: str = Field(
        default="email_password", description="Provedor de autenticação"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ["user", "admin", "superuser"]
        if v not in allowed_roles:
            raise ValueError(f"Role deve ser um de: {', '.join(allowed_roles)}")
        return v

    @field_validator("auth_provider")
    @classmethod
    def validate_auth_provider(cls, v):
        allowed_providers = ["email_password", "google_oauth2"]
        if v not in allowed_providers:
            raise ValueError(
                f"Auth provider deve ser um de: {', '.join(allowed_providers)}"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Nome completo é obrigatório")
        return v.strip()


class UserResponse(BaseModel):
    """Schema para resposta de usuário"""

    id: str = Field(description="ID único do usuário")
    email: str = Field(description="Email do usuário")
    full_name: str = Field(description="Nome completo")
    role: str = Field(description="Role do usuário")
    primary_municipality_id: Optional[str] = Field(
        description="ID da prefeitura principal"
    )
    municipality_ids: List[str] = Field(description="IDs das prefeituras")
    is_active: bool = Field(description="Se o usuário está ativo")
    email_verified: bool = Field(description="Se o email foi verificado")
    last_login: Optional[str] = Field(description="Data do último login (ISO format)")
    created_at: str = Field(description="Data de criação (ISO format)")
    has_pending_invitation: bool = Field(description="Se tem convite pendente")


class UserListResponse(BaseModel):
    """Schema para lista de usuários"""

    users: List[UserResponse] = Field(description="Lista de usuários")
    total: int = Field(description="Total de usuários")
    municipality_id: str = Field(description="ID da prefeitura")


class ResendInvitationResponse(BaseModel):
    """Schema para resposta de reenvio de convite"""

    message: str = Field(description="Mensagem de sucesso")
    email: str = Field(description="Email para o qual foi enviado")


class DeactivateUserResponse(BaseModel):
    """Schema para resposta de desativação de usuário"""

    message: str = Field(description="Mensagem de sucesso")
    user: UserResponse = Field(description="Dados do usuário desativado")


class UserStatsResponse(BaseModel):
    """Schema para estatísticas de usuários"""

    total_users: int = Field(description="Total de usuários")
    active_users: int = Field(description="Usuários ativos")
    pending_invitations: int = Field(description="Convites pendentes")
    users_by_role: dict = Field(description="Usuários por role")
    recent_logins: int = Field(description="Logins recentes (últimas 24h)")


class BulkInviteRequest(BaseModel):
    """Schema para convite em massa"""

    users: List[CreateUserRequest] = Field(
        min_items=1, max_items=50, description="Lista de usuários para convidar"
    )
    send_welcome_email: bool = Field(
        default=True, description="Se deve enviar email de boas-vindas"
    )


class BulkInviteResponse(BaseModel):
    """Schema para resposta de convite em massa"""

    total_requested: int = Field(description="Total de convites solicitados")
    successful_invites: int = Field(description="Convites enviados com sucesso")
    failed_invites: int = Field(description="Convites que falharam")
    errors: List[dict] = Field(description="Lista de erros ocorridos")
    created_users: List[UserResponse] = Field(
        description="Usuários criados com sucesso"
    )


class UpdateUserRoleRequest(BaseModel):
    """Schema para atualização de role de usuário"""

    role: str = Field(description="Nova role do usuário")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ["user", "admin", "superuser"]
        if v not in allowed_roles:
            raise ValueError(f"Role deve ser um de: {', '.join(allowed_roles)}")
        return v


class AddMunicipalityRequest(BaseModel):
    """Schema para adicionar prefeitura ao usuário"""

    municipality_id: UUID = Field(description="ID da prefeitura a ser adicionada")


class RemoveMunicipalityRequest(BaseModel):
    """Schema para remover prefeitura do usuário"""

    municipality_id: UUID = Field(description="ID da prefeitura a ser removida")


class UserActivityResponse(BaseModel):
    """Schema para atividade do usuário"""

    user_id: str = Field(description="ID do usuário")
    last_login: Optional[str] = Field(description="Último login")
    total_messages: int = Field(description="Total de mensagens enviadas")
    messages_this_month: int = Field(description="Mensagens este mês")
    favorite_topics: List[str] = Field(description="Tópicos mais consultados")
    active_sessions: int = Field(description="Sessões ativas")


class EmailTestRequest(BaseModel):
    """Schema para teste de envio de email"""

    email: EmailStr = Field(description="Email de destino para teste")
    template_type: str = Field(
        description="Tipo de template: invitation, welcome, reset"
    )

    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v):
        allowed_types = ["invitation", "welcome", "reset", "activated"]
        if v not in allowed_types:
            raise ValueError(
                f"Template type deve ser um de: {', '.join(allowed_types)}"
            )
        return v


class EmailTestResponse(BaseModel):
    """Schema para resposta de teste de email"""

    success: bool = Field(description="Se o email foi enviado com sucesso")
    message: str = Field(description="Mensagem de resultado")
    email: str = Field(description="Email de destino")
    template_type: str = Field(description="Tipo de template testado")
