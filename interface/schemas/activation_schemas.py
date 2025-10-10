from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ActivateAccountRequest(BaseModel):
    """Schema para ativação de conta com escolha de método de autenticação"""

    invitation_token: str = Field(description="Token de convite recebido por email")
    auth_provider: str = Field(
        default="email_password",
        description="Método de autenticação: email_password ou google_oauth2",
    )
    password: Optional[str] = Field(
        default=None, description="Senha (obrigatória para email_password)"
    )
    google_token: Optional[str] = Field(
        default=None, description="Token do Google (obrigatório para google_oauth2)"
    )

    @field_validator("auth_provider")
    @classmethod
    def validate_auth_provider(cls, v):
        allowed_providers = ["email_password", "google_oauth2"]
        if v not in allowed_providers:
            raise ValueError(
                f"Auth provider deve ser um de: {', '.join(allowed_providers)}"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v, info):
        # Se auth_provider é email_password, senha é obrigatória
        if info.data.get("auth_provider") == "email_password":
            if not v or len(v.strip()) < 6:
                raise ValueError("Senha deve ter pelo menos 6 caracteres")
        return v

    @field_validator("google_token")
    @classmethod
    def validate_google_token(cls, v, info):
        # Se auth_provider é google_oauth2, token é obrigatório
        if info.data.get("auth_provider") == "google_oauth2":
            if not v or len(v.strip()) < 10:
                raise ValueError("Token Google é obrigatório para autenticação OAuth2")
        return v


class ActivateAccountResponse(BaseModel):
    """Schema para resposta de ativação de conta"""

    success: bool = Field(description="Se a ativação foi bem-sucedida")
    message: str = Field(description="Mensagem de resultado")
    user_id: str = Field(description="ID do usuário ativado")
    auth_provider: str = Field(description="Método de autenticação configurado")
    next_step: str = Field(description="Próximo passo para o usuário")


class CheckInvitationRequest(BaseModel):
    """Schema para verificar convite antes da ativação"""

    invitation_token: str = Field(description="Token de convite")


class CheckInvitationResponse(BaseModel):
    """Schema para resposta de verificação de convite"""

    valid: bool = Field(description="Se o convite é válido")
    expired: bool = Field(description="Se o convite expirou")
    user_email: Optional[str] = Field(description="Email do usuário convidado")
    user_name: Optional[str] = Field(description="Nome do usuário convidado")
    invited_by: Optional[str] = Field(description="Nome de quem enviou o convite")
    expires_at: Optional[str] = Field(description="Data de expiração do convite")
    message: str = Field(description="Mensagem explicativa")
