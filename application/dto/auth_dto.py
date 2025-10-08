from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LoginEmailPasswordDTO:
    """DTO para login com email e senha"""

    email: str
    password: str


@dataclass
class LoginGoogleOAuth2DTO:
    """DTO para login com Google OAuth2"""

    google_token: str


@dataclass
class UserDTO:
    """DTO para dados do usuário"""

    id: str
    email: str
    full_name: str
    role: str
    primary_municipality_id: Optional[str]
    municipality_ids: List[str]
    is_active: bool
    email_verified: bool
    last_login: Optional[str]
    created_at: str


@dataclass
class LoginResponseDTO:
    """DTO para resposta de login"""

    access_token: str
    token_type: str
    user: UserDTO


@dataclass
class CreateUserDTO:
    """DTO para criação de usuário"""

    email: str
    full_name: str
    role: str
    primary_municipality_id: str
    municipality_ids: Optional[List[str]] = None
    auth_provider: str = "email_password"


@dataclass
class UserListDTO:
    """DTO para listagem de usuários"""

    id: str
    email: str
    full_name: str
    role: str
    primary_municipality_id: Optional[str]
    municipality_ids: List[str]
    is_active: bool
    email_verified: bool
    last_login: Optional[str]
    created_at: str
    has_pending_invitation: bool


@dataclass
class ActivateUserDTO:
    """DTO para ativação de usuário"""

    invitation_token: str
    password: Optional[str] = None
