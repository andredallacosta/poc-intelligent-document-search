import logging
from typing import List, Optional
from uuid import UUID

from application.dto.auth_dto import (
    ActivateUserDTO,
    CreateUserDTO,
    UserListDTO
)
from domain.entities.user import AuthProvider, User, UserRole
from domain.exceptions.auth_exceptions import (
    InsufficientPermissionsError,
    UserNotFoundError
)
from domain.repositories.user_repository import UserRepository
from domain.services.authentication_service import AuthenticationService
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId

logger = logging.getLogger(__name__)


class UserManagementUseCase:
    """Use case para gerenciamento de usuários"""
    
    def __init__(
        self,
        user_repo: UserRepository,
        auth_service: AuthenticationService
    ):
        self._user_repo = user_repo
        self._auth_service = auth_service
    
    async def create_user_with_invitation(
        self,
        request: CreateUserDTO,
        created_by: User
    ) -> UserListDTO:
        """Cria usuário e envia convite por email"""
        
        # 1. Verifica permissões
        self._validate_create_permissions(created_by, request.role, request.primary_municipality_id)
        
        # 2. Verifica se email já existe
        existing_user = await self._user_repo.find_by_email(request.email)
        if existing_user:
            raise ValueError("Email já cadastrado no sistema")
        
        # 3. Cria usuário com convite
        new_user = User.create_with_invitation(
            email=request.email,
            full_name=request.full_name,
            role=UserRole(request.role),
            primary_municipality_id=MunicipalityId(request.primary_municipality_id),
            invited_by=created_by.id,
            auth_provider=AuthProvider(request.auth_provider)
        )
        
        # 4. Adiciona prefeituras extras (se aplicável)
        if request.municipality_ids:
            for mid in request.municipality_ids:
                if mid != request.primary_municipality_id:
                    new_user.add_municipality(MunicipalityId(mid))
        
        # 5. Salva no banco
        await self._user_repo.save(new_user)
        
        logger.info(
            "user_created_with_invitation",
            extra={
                "new_user_id": str(new_user.id.value),
                "email": new_user.email,
                "role": new_user.role.value,
                "created_by": str(created_by.id.value)
            }
        )
        
        return self._user_to_dto(new_user)
    
    async def activate_user_account(self, request: ActivateUserDTO) -> UserListDTO:
        """Ativa conta de usuário via token de convite"""
        
        # 1. Busca usuário por token
        user = await self._user_repo.find_by_invitation_token(request.invitation_token)
        if not user:
            raise UserNotFoundError("Token de convite inválido")
        
        # 2. Ativa conta
        password_hash = None
        if request.password:
            password_hash = self._auth_service.hash_password(request.password)
        
        user.activate_account(password_hash)
        
        # 3. Salva no banco
        await self._user_repo.save(user)
        
        logger.info(
            "user_account_activated",
            extra={
                "user_id": str(user.id.value),
                "email": user.email
            }
        )
        
        return self._user_to_dto(user)
    
    async def list_users_by_municipality(
        self,
        municipality_id: UUID,
        requesting_user: User,
        limit: Optional[int] = None
    ) -> List[UserListDTO]:
        """Lista usuários de uma prefeitura"""
        
        municipality_id_vo = MunicipalityId(municipality_id)
        
        # 1. Verifica permissões
        if not requesting_user.can_manage_municipality(municipality_id_vo):
            raise InsufficientPermissionsError("Sem permissão para listar usuários desta prefeitura")
        
        # 2. Busca usuários
        users = await self._user_repo.find_by_municipality_id(municipality_id_vo, limit=limit)
        
        return [self._user_to_dto(user) for user in users]
    
    async def deactivate_user(
        self,
        user_id: UUID,
        requesting_user: User
    ) -> UserListDTO:
        """Desativa usuário"""
        
        # 1. Busca usuário
        user = await self._user_repo.find_by_id(UserId(user_id))
        if not user:
            raise UserNotFoundError("Usuário não encontrado")
        
        # 2. Verifica permissões
        if not requesting_user.can_manage_municipality(user.primary_municipality_id):
            raise InsufficientPermissionsError("Sem permissão para desativar este usuário")
        
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
                "deactivated_by": str(requesting_user.id.value)
            }
        )
        
        return self._user_to_dto(user)
    
    def _validate_create_permissions(
        self,
        created_by: User,
        target_role: str,
        target_municipality_id: str
    ) -> None:
        """Valida permissões para criar usuário"""
        target_municipality_id_vo = MunicipalityId(target_municipality_id)
        
        # Superuser pode criar qualquer usuário
        if created_by.role == UserRole.SUPERUSER:
            return
        
        # Admin só pode criar usuários na sua prefeitura
        if created_by.role == UserRole.ADMIN:
            if not created_by.can_manage_municipality(target_municipality_id_vo):
                raise InsufficientPermissionsError("Sem permissão para criar usuários nesta prefeitura")
            
            # Admin não pode criar superuser ou admin
            if target_role in ["superuser", "admin"]:
                raise InsufficientPermissionsError("Admins não podem criar superusers ou outros admins")
            
            return
        
        # Usuários comuns não podem criar ninguém
        raise InsufficientPermissionsError("Usuários comuns não podem criar outros usuários")
    
    def _user_to_dto(self, user: User) -> UserListDTO:
        """Converte User para DTO"""
        return UserListDTO(
            id=str(user.id.value),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            primary_municipality_id=str(user.primary_municipality_id.value) if user.primary_municipality_id else None,
            municipality_ids=[str(mid.value) for mid in user.municipality_ids],
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat(),
            has_pending_invitation=user.invitation_token is not None
        )
