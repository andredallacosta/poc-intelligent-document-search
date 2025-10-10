import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from application.dto.auth_dto import CreateUserDTO, UserListDTO
from application.use_cases.user_management_use_case import UserManagementUseCase
from domain.exceptions.auth_exceptions import (
    EmailDeliveryError,
    InsufficientPermissionsError,
    UserNotFoundError,
)
from interface.dependencies.container import get_user_management_use_case
from interface.middleware.auth_middleware import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/create", response_model=UserListDTO)
async def create_user_with_invitation(
    request: CreateUserDTO,
    current_user: AuthenticatedUser,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    """
    Cria novo usuário e envia convite por email

    Requer permissões:
    - SUPERUSER: Pode criar qualquer usuário
    - ADMIN: Pode criar apenas usuários comuns na sua prefeitura
    """
    try:
        new_user = await user_management_use_case.create_user_with_invitation(
            request=request,
            created_by=current_user,
        )

        logger.info(
            "user_creation_requested",
            extra={
                "created_user_id": new_user.id,
                "created_by": str(current_user.id.value),
                "email": new_user.email,
                "role": new_user.role,
            },
        )

        return new_user

    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_permissions",
                "message": str(e),
                "code": e.error_code,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(e),
                "code": "VALIDATION_ERROR",
            },
        )
    except EmailDeliveryError as e:
        # Usuário foi criado, mas email falhou
        logger.warning(
            "user_created_but_email_failed",
            extra={
                "email": request.email,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=201,  # Created, mas com aviso
            detail={
                "error": "email_delivery_failed",
                "message": f"Usuário criado com sucesso, mas falha no envio do email: {str(e)}",
                "code": e.error_code,
            },
        )
    except Exception as e:
        logger.error(
            "user_creation_failed",
            extra={
                "email": request.email,
                "created_by": str(current_user.id.value),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "Erro interno na criação do usuário",
                "code": "INTERNAL_ERROR",
            },
        )


@router.get("/list", response_model=List[UserListDTO])
async def list_users_by_municipality(
    current_user: AuthenticatedUser,
    municipality_id: UUID = Query(description="ID da prefeitura"),
    limit: Optional[int] = Query(
        default=50, le=100, description="Limite de resultados"
    ),
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    """
    Lista usuários de uma prefeitura

    Requer permissões:
    - SUPERUSER: Pode listar usuários de qualquer prefeitura
    - ADMIN: Pode listar apenas usuários das suas prefeituras
    """
    try:
        users = await user_management_use_case.list_users_by_municipality(
            municipality_id=municipality_id,
            requesting_user=current_user,
            limit=limit,
        )

        logger.info(
            "users_listed",
            extra={
                "municipality_id": str(municipality_id),
                "requested_by": str(current_user.id.value),
                "count": len(users),
            },
        )

        return users

    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_permissions",
                "message": str(e),
                "code": e.error_code,
            },
        )
    except Exception as e:
        logger.error(
            "user_listing_failed",
            extra={
                "municipality_id": str(municipality_id),
                "requested_by": str(current_user.id.value),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "Erro interno na listagem de usuários",
                "code": "INTERNAL_ERROR",
            },
        )


@router.post("/{user_id}/deactivate", response_model=UserListDTO)
async def deactivate_user(
    user_id: UUID,
    current_user: AuthenticatedUser,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    """
    Desativa usuário (soft delete)

    Requer permissões:
    - SUPERUSER: Pode desativar qualquer usuário
    - ADMIN: Pode desativar apenas usuários das suas prefeituras

    Restrições:
    - Não é possível desativar a própria conta
    """
    try:
        deactivated_user = await user_management_use_case.deactivate_user(
            user_id=user_id,
            requesting_user=current_user,
        )

        logger.info(
            "user_deactivated",
            extra={
                "deactivated_user_id": str(user_id),
                "deactivated_by": str(current_user.id.value),
            },
        )

        return deactivated_user

    except UserNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "user_not_found",
                "message": str(e),
                "code": e.error_code,
            },
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_permissions",
                "message": str(e),
                "code": e.error_code,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(e),
                "code": "VALIDATION_ERROR",
            },
        )
    except Exception as e:
        logger.error(
            "user_deactivation_failed",
            extra={
                "user_id": str(user_id),
                "requested_by": str(current_user.id.value),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "Erro interno na desativação do usuário",
                "code": "INTERNAL_ERROR",
            },
        )


@router.get("/me", response_model=UserListDTO)
async def get_current_user_info(
    current_user: AuthenticatedUser,
):
    """
    Retorna informações do usuário autenticado
    """
    try:
        user_dto = UserListDTO(
            id=str(current_user.id.value),
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role.value,
            primary_municipality_id=(
                str(current_user.primary_municipality_id.value)
                if current_user.primary_municipality_id
                else None
            ),
            municipality_ids=[str(mid.value) for mid in current_user.municipality_ids],
            is_active=current_user.is_active,
            email_verified=current_user.email_verified,
            last_login=(
                current_user.last_login.isoformat() if current_user.last_login else None
            ),
            created_at=current_user.created_at.isoformat(),
            has_pending_invitation=current_user.invitation_token is not None,
        )

        return user_dto

    except Exception as e:
        logger.error(
            "get_current_user_failed",
            extra={
                "user_id": str(current_user.id.value),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "Erro interno ao obter informações do usuário",
                "code": "INTERNAL_ERROR",
            },
        )


@router.post("/{user_id}/resend-invitation")
async def resend_invitation_email(
    user_id: UUID,
    current_user: AuthenticatedUser,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    """
    Reenvia email de convite para usuário com convite pendente

    Requer permissões:
    - SUPERUSER: Pode reenviar para qualquer usuário
    - ADMIN: Pode reenviar apenas para usuários das suas prefeituras
    """
    try:
        # Busca usuário
        from domain.value_objects.user_id import UserId
        from interface.dependencies.container import get_postgres_user_repository

        async for session in get_postgres_user_repository():
            user_repo = session
            break

        target_user = await user_repo.find_by_id(UserId(user_id))
        if not target_user:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "user_not_found",
                    "message": "Usuário não encontrado",
                    "code": "USER_NOT_FOUND",
                },
            )

        # Verifica se tem convite pendente
        if not target_user.invitation_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_pending_invitation",
                    "message": "Usuário não possui convite pendente",
                    "code": "NO_PENDING_INVITATION",
                },
            )

        # Verifica permissões
        if not current_user.can_manage_municipality(
            target_user.primary_municipality_id
        ):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_permissions",
                    "message": "Sem permissão para gerenciar este usuário",
                    "code": "INSUFFICIENT_PERMISSIONS",
                },
            )

        # Reenvia email
        from interface.dependencies.container import get_email_service

        email_service = get_email_service()

        await email_service.send_invitation_email(
            email=target_user.email,
            full_name=target_user.full_name,
            invitation_token=target_user.invitation_token,
            invited_by_name=current_user.full_name,
        )

        logger.info(
            "invitation_email_resent",
            extra={
                "target_user_id": str(user_id),
                "resent_by": str(current_user.id.value),
                "email": target_user.email,
            },
        )

        return {
            "message": "Email de convite reenviado com sucesso",
            "email": target_user.email,
        }

    except HTTPException:
        raise
    except EmailDeliveryError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "email_delivery_failed",
                "message": f"Falha no envio do email: {str(e)}",
                "code": e.error_code,
            },
        )
    except Exception as e:
        logger.error(
            "resend_invitation_failed",
            extra={
                "user_id": str(user_id),
                "requested_by": str(current_user.id.value),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "Erro interno ao reenviar convite",
                "code": "INTERNAL_ERROR",
            },
        )
