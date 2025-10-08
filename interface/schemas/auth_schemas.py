from typing import List, Optional

from pydantic import BaseModel, Field


class LoginEmailPasswordRequest(BaseModel):
    """Schema para login com email e senha"""

    email: str = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=6, description="Senha do usuário")


class LoginGoogleOAuth2Request(BaseModel):
    """Schema para login com Google OAuth2"""

    google_token: str = Field(..., description="Token do Google OAuth2")


class GoogleAuthUrlResponse(BaseModel):
    """Schema para URL de autenticação Google"""

    auth_url: str = Field(..., description="URL para autenticação Google")
    redirect_uri: str = Field(..., description="URI de redirecionamento")


class UserResponse(BaseModel):
    """Schema para dados do usuário"""

    id: str = Field(..., description="ID do usuário")
    email: str = Field(..., description="Email do usuário")
    full_name: str = Field(..., description="Nome completo do usuário")
    role: str = Field(..., description="Role do usuário")
    primary_municipality_id: Optional[str] = Field(
        None, description="ID da prefeitura principal"
    )
    municipality_ids: List[str] = Field(
        default_factory=list, description="IDs das prefeituras"
    )
    is_active: bool = Field(..., description="Se o usuário está ativo")
    email_verified: bool = Field(..., description="Se o email foi verificado")
    last_login: Optional[str] = Field(None, description="Último login")
    created_at: str = Field(..., description="Data de criação")


class LoginResponse(BaseModel):
    """Schema para resposta de login"""

    access_token: str = Field(..., description="Token JWT de acesso")
    token_type: str = Field(..., description="Tipo do token")
    user: UserResponse = Field(..., description="Dados do usuário")


class CreateUserRequest(BaseModel):
    """Schema para criação de usuário"""

    email: str = Field(..., description="Email do usuário")
    full_name: str = Field(
        ..., min_length=2, max_length=255, description="Nome completo"
    )
    role: str = Field(
        ..., description="Role do usuário", pattern="^(superuser|admin|user)$"
    )
    primary_municipality_id: str = Field(..., description="ID da prefeitura principal")
    municipality_ids: Optional[List[str]] = Field(
        None, description="IDs das prefeituras adicionais"
    )
    auth_provider: str = Field(
        "email_password",
        description="Provedor de autenticação",
        pattern="^(email_password|google_oauth2)$",
    )


class UserListResponse(BaseModel):
    """Schema para listagem de usuários"""

    id: str = Field(..., description="ID do usuário")
    email: str = Field(..., description="Email do usuário")
    full_name: str = Field(..., description="Nome completo do usuário")
    role: str = Field(..., description="Role do usuário")
    primary_municipality_id: Optional[str] = Field(
        None, description="ID da prefeitura principal"
    )
    municipality_ids: List[str] = Field(
        default_factory=list, description="IDs das prefeituras"
    )
    is_active: bool = Field(..., description="Se o usuário está ativo")
    email_verified: bool = Field(..., description="Se o email foi verificado")
    last_login: Optional[str] = Field(None, description="Último login")
    created_at: str = Field(..., description="Data de criação")
    has_pending_invitation: bool = Field(..., description="Se tem convite pendente")


class ActivateUserRequest(BaseModel):
    """Schema para ativação de usuário"""

    invitation_token: str = Field(..., description="Token de convite")
    password: Optional[str] = Field(
        None, min_length=6, description="Senha (obrigatória para email/senha)"
    )


class ErrorResponse(BaseModel):
    """Schema para respostas de erro"""

    error: str = Field(..., description="Tipo do erro")
    message: str = Field(..., description="Mensagem do erro")
    code: str = Field(..., description="Código do erro")
