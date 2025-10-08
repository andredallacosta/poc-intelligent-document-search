import logging
from typing import Tuple

from application.dto.auth_dto import (
    LoginEmailPasswordDTO,
    LoginGoogleOAuth2DTO,
    LoginResponseDTO,
    UserDTO
)
from domain.entities.user import User
from domain.services.authentication_service import AuthenticationService

logger = logging.getLogger(__name__)


class AuthenticationUseCase:
    """Use case para autenticação de usuários"""
    
    def __init__(self, auth_service: AuthenticationService):
        self._auth_service = auth_service
    
    async def login_email_password(self, request: LoginEmailPasswordDTO) -> LoginResponseDTO:
        """Login com email e senha"""
        user, jwt_token = await self._auth_service.authenticate_email_password(
            email=request.email,
            password=request.password
        )
        
        return self._create_login_response(user, jwt_token)
    
    async def login_google_oauth2(self, request: LoginGoogleOAuth2DTO) -> LoginResponseDTO:
        """Login com Google OAuth2"""
        user, jwt_token = await self._auth_service.authenticate_google_oauth2(
            google_token=request.google_token
        )
        
        return self._create_login_response(user, jwt_token)
    
    async def verify_token(self, token: str) -> UserDTO:
        """Verifica JWT e retorna dados do usuário"""
        user = await self._auth_service.verify_jwt_token(token)
        
        return UserDTO(
            id=str(user.id.value),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            primary_municipality_id=str(user.primary_municipality_id.value) if user.primary_municipality_id else None,
            municipality_ids=[str(mid.value) for mid in user.municipality_ids],
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat()
        )
    
    def _create_login_response(self, user: User, jwt_token: str) -> LoginResponseDTO:
        """Cria resposta de login padronizada"""
        user_dto = UserDTO(
            id=str(user.id.value),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            primary_municipality_id=str(user.primary_municipality_id.value) if user.primary_municipality_id else None,
            municipality_ids=[str(mid.value) for mid in user.municipality_ids],
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat()
        )
        
        return LoginResponseDTO(
            access_token=jwt_token,
            token_type="bearer",
            user=user_dto
        )
