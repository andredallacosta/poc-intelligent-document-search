import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from application.dto.auth_dto import ActivateUserDTO, CreateUserDTO, UserListDTO
from domain.entities.user import AuthProvider, User, UserRole
from domain.exceptions.auth_exceptions import (
    EmailDeliveryError,
    InsufficientPermissionsError,
    RateLimitExceededError,
    UserNotFoundError,
)
from domain.repositories.user_repository import UserRepository
from domain.services.authentication_service import AuthenticationService
from domain.services.email_rate_limiter import EmailRateLimiter
from domain.services.email_service import EmailService
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId

logger = logging.getLogger(__name__)


class UserManagementUseCase:
    """Use case para gerenciamento de usuários"""

    def __init__(
        self,
        user_repo: UserRepository,
        auth_service: AuthenticationService,
        email_service: EmailService,
        redis_queue=None,
        email_rate_limiter: Optional[EmailRateLimiter] = None,
    ):
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._email_service = email_service
        self._redis_queue = redis_queue
        self._email_rate_limiter = email_rate_limiter

    async def create_user_with_invitation(
        self, request: CreateUserDTO, created_by: User
    ) -> UserListDTO:
        """Cria usuário e envia convite por email"""

        # 1. Verifica permissões
        self._validate_create_permissions(
            created_by, request.role, request.primary_municipality_id
        )

        # 2. Verifica se email já existe
        existing_user = await self._user_repo.find_by_email(request.email)
        if existing_user:
            raise ValueError("Email já cadastrado no sistema")

        # 3. Cria usuário com convite (auth_provider será definido na ativação)
        new_user = User.create_with_invitation(
            email=request.email,
            full_name=request.full_name,
            role=UserRole(request.role),
            primary_municipality_id=MunicipalityId(request.primary_municipality_id),
            invited_by=created_by.id,
            # Não definimos auth_provider - usuário escolherá na ativação
        )

        # 4. Adiciona prefeituras extras (se aplicável)
        if request.municipality_ids:
            for mid in request.municipality_ids:
                if mid != request.primary_municipality_id:
                    new_user.add_municipality(MunicipalityId(mid))

        # 5. Verifica rate limiting (antes de salvar no banco)
        if self._email_rate_limiter:
            if not self._email_rate_limiter.check_user_limit(str(created_by.id.value)):
                raise RateLimitExceededError(
                    "Limite de 10 convites por minuto atingido. Aguarde antes de enviar novos convites."
                )

            if not self._email_rate_limiter.check_global_limit():
                raise RateLimitExceededError(
                    "Sistema temporariamente ocupado. Tente novamente em alguns segundos."
                )

        # 6. Salva no banco
        await self._user_repo.save(new_user)

        # 7. Enfileira email de convite (assíncrono)
        if self._redis_queue:
            try:
                job_id = self._redis_queue.enqueue_email_sending(
                    email_type="invitation",
                    recipient_email=new_user.email,
                    recipient_name=new_user.full_name,
                    template_data={
                        "invitation_token": new_user.invitation_token,
                        "invited_by_name": created_by.full_name,
                        "municipality_name": None,
                    },
                    priority="high",
                )

                logger.info(
                    "invitation_email_enqueued",
                    extra={
                        "user_id": str(new_user.id.value),
                        "email": new_user.email,
                        "job_id": job_id,
                    },
                )
            except Exception as e:
                logger.error(
                    "invitation_email_enqueue_failed",
                    extra={
                        "user_id": str(new_user.id.value),
                        "email": new_user.email,
                        "error": str(e),
                    },
                )
                raise EmailDeliveryError(
                    "Falha ao enfileirar email de convite. Tente novamente."
                )
        else:
            try:
                await self._email_service.send_invitation_email(
                    email=new_user.email,
                    full_name=new_user.full_name,
                    invitation_token=new_user.invitation_token,
                    invited_by_name=created_by.full_name,
                )

                logger.info(
                    "invitation_email_sent",
                    extra={
                        "user_id": str(new_user.id.value),
                        "email": new_user.email,
                    },
                )
            except EmailDeliveryError:
                logger.error(
                    "invitation_email_delivery_failed",
                    extra={
                        "user_id": str(new_user.id.value),
                        "email": new_user.email,
                    },
                )
                raise
            except Exception as e:
                logger.warning(
                    "invitation_email_failed",
                    extra={
                        "user_id": str(new_user.id.value),
                        "email": new_user.email,
                        "error": str(e),
                    },
                )

        logger.info(
            "user_created_with_invitation",
            extra={
                "new_user_id": str(new_user.id.value),
                "email": new_user.email,
                "role": new_user.role.value,
                "created_by": str(created_by.id.value),
            },
        )

        return await self._user_to_dto(new_user)

    async def activate_user_account(self, request: ActivateUserDTO) -> UserListDTO:
        """Ativa conta de usuário via token de convite com escolha de auth_provider"""

        # 1. Busca usuário por token
        user = await self._user_repo.find_by_invitation_token(request.invitation_token)
        if not user:
            raise UserNotFoundError("Token de convite inválido")

        # 2. Processa ativação baseada no auth_provider escolhido
        password_hash = None
        google_id = None
        auth_provider = AuthProvider(request.auth_provider)

        if auth_provider == AuthProvider.EMAIL_PASSWORD:
            if not request.password:
                raise ValueError("Senha obrigatória para ativação com email/senha")
            password_hash = self._auth_service.hash_password(request.password)

        elif auth_provider == AuthProvider.GOOGLE_OAUTH2:
            if not request.google_token:
                raise ValueError(
                    "Token Google obrigatório para ativação com Google OAuth2"
                )

            # Valida token Google e extrai google_id
            try:
                google_user_info = await self._auth_service._verify_google_token(
                    request.google_token
                )
                google_id = google_user_info["sub"]

                # Verifica se o email do token Google confere com o email do convite
                if google_user_info["email"].lower() != user.email.lower():
                    raise ValueError(
                        "Email do token Google não confere com o email do convite"
                    )

            except Exception as e:
                raise ValueError(f"Token Google inválido: {str(e)}")

        # 3. Ativa conta com o método escolhido
        user.activate_account(
            password_hash=password_hash,
            auth_provider=auth_provider,
            google_id=google_id,
        )

        # 3. Salva no banco
        await self._user_repo.save(user)

        # 4. Enfileira emails de confirmação e boas-vindas (assíncrono)
        if self._redis_queue:
            try:
                job_id_activated = self._redis_queue.enqueue_email_sending(
                    email_type="account_activated",
                    recipient_email=user.email,
                    recipient_name=user.full_name,
                    template_data={},
                    priority="high",
                )

                logger.info(
                    "activation_confirmation_email_enqueued",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                        "job_id": job_id_activated,
                    },
                )

                job_id_welcome = self._redis_queue.enqueue_email_sending(
                    email_type="welcome",
                    recipient_email=user.email,
                    recipient_name=user.full_name,
                    template_data={"municipality_name": None},
                    priority="normal",
                )

                logger.info(
                    "welcome_email_enqueued",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                        "job_id": job_id_welcome,
                    },
                )
            except Exception as e:
                logger.warning(
                    "activation_emails_enqueue_failed",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                        "error": str(e),
                    },
                )
        else:
            try:
                await self._email_service.send_account_activated_email(
                    email=user.email,
                    full_name=user.full_name,
                )

                logger.info(
                    "activation_confirmation_email_sent",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                    },
                )
            except Exception as e:
                logger.warning(
                    "activation_confirmation_email_failed",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                        "error": str(e),
                    },
                )

            try:
                await self._email_service.send_welcome_email(
                    email=user.email,
                    full_name=user.full_name,
                )

                logger.info(
                    "welcome_email_sent",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                    },
                )
            except Exception as e:
                logger.warning(
                    "welcome_email_failed",
                    extra={
                        "user_id": str(user.id.value),
                        "email": user.email,
                        "error": str(e),
                    },
                )

        logger.info(
            "user_account_activated",
            extra={"user_id": str(user.id.value), "email": user.email},
        )

        return await self._user_to_dto(user)

    async def list_users_by_municipality(
        self, municipality_id: UUID, requesting_user: User, limit: Optional[int] = None
    ) -> List[UserListDTO]:
        """Lista usuários de uma prefeitura"""

        municipality_id_vo = MunicipalityId(municipality_id)

        # 1. Verifica permissões
        if not requesting_user.can_manage_municipality(municipality_id_vo):
            raise InsufficientPermissionsError(
                "Sem permissão para listar usuários desta prefeitura"
            )

        # 2. Busca usuários
        users = await self._user_repo.find_by_municipality_id(
            municipality_id_vo, limit=limit
        )

        user_dtos = await asyncio.gather(*[self._user_to_dto(user) for user in users])
        return list(user_dtos)

    async def deactivate_user(
        self, user_id: UUID, requesting_user: User
    ) -> UserListDTO:
        """Desativa usuário"""

        # 1. Busca usuário
        user = await self._user_repo.find_by_id(UserId(user_id))
        if not user:
            raise UserNotFoundError("Usuário não encontrado")

        # 2. Verifica permissões
        if not requesting_user.can_manage_municipality(user.primary_municipality_id):
            raise InsufficientPermissionsError(
                "Sem permissão para desativar este usuário"
            )

        # 3. Não pode desativar a si mesmo
        if user.id == requesting_user.id:
            raise ValueError("Não é possível desativar sua própria conta")

        # 4. Desativa
        user.deactivate()
        await self._user_repo.save(user)

        logger.info(
            "user_deactivated",
            extra={
                "user_id": str(user.id.value),
                "deactivated_by": str(requesting_user.id.value),
            },
        )

        return await self._user_to_dto(user)

    def _validate_create_permissions(
        self, created_by: User, target_role: str, target_municipality_id: str
    ) -> None:
        """Valida permissões para criar usuário"""
        target_municipality_id_vo = MunicipalityId(target_municipality_id)

        # Superuser pode criar qualquer usuário
        if created_by.role == UserRole.SUPERUSER:
            return

        # Admin só pode criar usuários na sua prefeitura
        if created_by.role == UserRole.ADMIN:
            if not created_by.can_manage_municipality(target_municipality_id_vo):
                raise InsufficientPermissionsError(
                    "Sem permissão para criar usuários nesta prefeitura"
                )

            # Admin não pode criar superuser ou admin
            if target_role in ["superuser", "admin"]:
                raise InsufficientPermissionsError(
                    "Admins não podem criar superusers ou outros admins"
                )

            return

        # Usuários comuns não podem criar ninguém
        raise InsufficientPermissionsError(
            "Usuários comuns não podem criar outros usuários"
        )

    async def _user_to_dto(self, user: User) -> UserListDTO:
        """Converte User para DTO"""
        invited_by_name = None
        if user.invited_by:
            invited_by_user = await self._user_repo.find_by_id(user.invited_by)
            if invited_by_user:
                invited_by_name = invited_by_user.full_name

        return UserListDTO(
            id=str(user.id.value),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            primary_municipality_id=(
                str(user.primary_municipality_id.value)
                if user.primary_municipality_id
                else None
            ),
            municipality_ids=[str(mid.value) for mid in user.municipality_ids],
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat(),
            has_pending_invitation=user.invitation_token is not None,
            invited_by_name=invited_by_name,
        )
