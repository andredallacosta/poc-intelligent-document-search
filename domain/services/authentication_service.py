import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
import httpx
import jwt
from google.auth.transport import requests
from google.oauth2 import id_token

from domain.entities.user import User
from domain.exceptions.auth_exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserInactiveError,
    UserNotFoundError,
)
from domain.repositories.user_repository import UserRepository
from domain.value_objects.auth_provider import AuthProvider
from domain.value_objects.user_id import UserId

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Serviço de domínio para autenticação de usuários"""

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        jwt_expiry_days: int = 3,
        google_client_id: Optional[str] = None,
        google_client_secret: Optional[str] = None,
        google_redirect_uri: Optional[str] = None,
    ):
        self._user_repo = user_repository
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._jwt_expiry_days = jwt_expiry_days
        self._google_client_id = google_client_id
        self._google_client_secret = google_client_secret
        self._google_redirect_uri = google_redirect_uri

    async def authenticate_email_password(
        self, email: str, password: str
    ) -> Tuple[User, str]:
        """Autentica usuário com email/senha e retorna JWT"""
        try:
            # 1. Busca usuário por email
            user = await self._user_repo.find_by_email(email)
            if not user:
                raise UserNotFoundError("Usuário não encontrado")

            # 2. Verifica se está ativo
            if not user.is_active:
                raise UserInactiveError("Conta desativada")

            # 3. Verifica provider
            if user.auth_provider != AuthProvider.EMAIL_PASSWORD:
                raise InvalidCredentialsError("Use login com Google para esta conta")

            # 4. Verifica senha
            if not user.password_hash or not self._verify_password(
                password, user.password_hash
            ):
                raise InvalidCredentialsError("Email ou senha incorretos")

            # 5. Atualiza último login
            user.update_last_login()
            await self._user_repo.update(user)

            # 6. Gera JWT
            jwt_token = self._generate_jwt(user)

            logger.info(
                "user_login_success",
                extra={
                    "user_id": str(user.id.value),
                    "email": user.email,
                    "role": user.role.value,
                    "auth_provider": "email_password",
                },
            )

            return user, jwt_token

        except (UserNotFoundError, UserInactiveError, InvalidCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Erro na autenticação email/senha: {e}")
            raise AuthenticationError("Erro interno na autenticação")

    async def authenticate_google_oauth2(self, google_token: str) -> Tuple[User, str]:
        """Autentica usuário com Google OAuth2 e retorna JWT"""
        try:
            # 1. Verifica se é um código de autorização ou ID token
            if google_token.startswith("4/") or len(google_token) > 500:
                # É um código de autorização, precisa trocar por ID token
                google_user_info = await self._exchange_code_for_user_info(google_token)
            else:
                # É um ID token, valida diretamente
                google_user_info = await self._verify_google_token(google_token)

            # 2. Busca usuário por Google ID
            user = await self._user_repo.find_by_google_id(google_user_info["sub"])

            if not user:
                # Tenta buscar por email (caso tenha mudado de provider)
                user = await self._user_repo.find_by_email(google_user_info["email"])

                if user and user.auth_provider == AuthProvider.EMAIL_PASSWORD:
                    raise InvalidCredentialsError(
                        "Use login com email/senha para esta conta"
                    )

                if not user:
                    raise UserNotFoundError(
                        "Usuário não encontrado. Solicite convite ao administrador."
                    )

            # 3. Verifica se está ativo
            if not user.is_active:
                raise UserInactiveError("Conta desativada")

            # 4. Atualiza dados do Google se necessário
            if user.google_id != google_user_info["sub"]:
                user.google_id = google_user_info["sub"]
                user.email_verified = google_user_info.get("email_verified", False)
                await self._user_repo.save(user)

            # 5. Atualiza último login
            user.update_last_login()
            await self._user_repo.save(user)

            # 6. Gera JWT
            jwt_token = self._generate_jwt(user)

            logger.info(
                "user_login_success",
                extra={
                    "user_id": str(user.id.value),
                    "email": user.email,
                    "role": user.role.value,
                    "auth_provider": "google_oauth2",
                },
            )

            return user, jwt_token

        except (UserNotFoundError, UserInactiveError, InvalidCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Erro na autenticação Google OAuth2: {e}")
            raise AuthenticationError("Erro interno na autenticação")

    async def verify_jwt_token(self, token: str) -> User:
        """Verifica JWT e retorna usuário autenticado"""
        try:
            # 1. Decodifica JWT
            payload = jwt.decode(
                token, self._jwt_secret, algorithms=[self._jwt_algorithm]
            )

            # 2. Extrai dados do payload
            user_id = UserId.from_string(payload.get("user_id"))
            exp = payload.get("exp")

            if not user_id or not exp:
                raise InvalidTokenError("Token inválido")

            # 3. Verifica expiração
            if datetime.utcnow().timestamp() > exp:
                raise InvalidTokenError("Token expirado")

            # 4. Busca usuário
            user = await self._user_repo.find_by_id(user_id)
            if not user:
                raise InvalidTokenError("Usuário não encontrado")

            # 5. Verifica se ainda está ativo
            if not user.is_active:
                raise InvalidTokenError("Conta desativada")

            return user

        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Token expirado")
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Token inválido")
        except InvalidTokenError:
            # Re-raise domain exceptions without wrapping
            raise
        except Exception as e:
            logger.error(f"Erro na verificação do JWT: {e}")
            raise InvalidTokenError("Erro na verificação do token")

    def _generate_jwt(self, user: User) -> str:
        """Gera JWT para usuário autenticado"""
        now = datetime.utcnow()
        exp = now + timedelta(days=self._jwt_expiry_days)

        payload = {
            "user_id": str(user.id.value),
            "email": user.email,
            "role": user.role.value,
            "primary_municipality_id": (
                str(user.primary_municipality_id.value)
                if user.primary_municipality_id
                else None
            ),
            "municipality_ids": [str(mid.value) for mid in user.municipality_ids],
            "iat": now.timestamp(),
            "exp": exp.timestamp(),
            "iss": "intelligent-document-search",
            "sub": str(user.id.value),
        }

        return jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica senha usando bcrypt"""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except Exception:
            return False

    def hash_password(self, password: str) -> str:
        """Gera hash da senha usando bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    async def _exchange_code_for_user_info(self, authorization_code: str) -> dict:
        """Troca código de autorização por informações do usuário"""
        if not self._google_client_id or not self._google_client_secret:
            raise AuthenticationError("Google OAuth2 não configurado completamente")

        try:
            # 1. Troca código por tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": self._google_client_id,
                "client_secret": self._google_client_secret,
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": self._google_redirect_uri,
            }

            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data)
                token_response.raise_for_status()
                tokens = token_response.json()

            # 2. Verifica o ID token recebido
            id_token_str = tokens.get("id_token")
            if not id_token_str:
                raise InvalidTokenError("ID token não recebido do Google")

            return await self._verify_google_token(id_token_str)

        except httpx.HTTPError as e:
            logger.error(f"Erro ao trocar código por token: {e}")
            raise InvalidTokenError("Código de autorização inválido")
        except Exception as e:
            logger.error(f"Erro na troca de código: {e}")
            raise AuthenticationError("Erro interno na autenticação Google")

    async def _verify_google_token(self, token: str) -> dict:
        """Verifica token do Google OAuth2"""
        if not self._google_client_id:
            raise AuthenticationError("Google OAuth2 não configurado")

        try:
            # Verifica token com Google
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), self._google_client_id
            )

            # Verifica issuer
            if idinfo["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise InvalidTokenError("Token Google inválido")

            return idinfo

        except ValueError as e:
            raise InvalidTokenError(f"Token Google inválido: {e}")
