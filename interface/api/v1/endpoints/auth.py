import logging
from typing import List
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.dto.auth_dto import (
    ActivateUserDTO,
    LoginEmailPasswordDTO,
    LoginGoogleOAuth2DTO,
    UserDTO,
)
from application.use_cases.authentication_use_case import AuthenticationUseCase
from application.use_cases.user_management_use_case import UserManagementUseCase
from domain.exceptions.auth_exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserInactiveError,
    UserNotFoundError,
)
from infrastructure.config.settings import settings
from interface.dependencies.container import (
    get_authentication_use_case,
    get_user_management_use_case,
)
from interface.middleware.auth_middleware import get_authenticated_user
from interface.schemas.auth_schemas import (
    ActivateUserRequest,
    CreateUserRequest,
    ErrorResponse,
    GoogleAuthUrlResponse,
    LoginEmailPasswordRequest,
    LoginGoogleOAuth2Request,
    LoginResponse,
    UserListResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Credenciais inválidas"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Login com email e senha",
    description="Autentica usuário com email e senha, retorna JWT token",
)
async def login_email_password(
    request: LoginEmailPasswordRequest,
    auth_use_case: AuthenticationUseCase = Depends(get_authentication_use_case),
):
    try:
        login_dto = LoginEmailPasswordDTO(
            email=request.email, password=request.password
        )

        response = await auth_use_case.login_email_password(login_dto)

        return LoginResponse(
            access_token=response.access_token,
            token_type=response.token_type,
            user=UserResponse(**response.user.__dict__),
        )

    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_credentials",
                "message": str(e),
                "code": e.error_code,
            },
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "user_not_found", "message": str(e), "code": e.error_code},
        )
    except UserInactiveError as e:
        raise HTTPException(
            status_code=403,
            detail={"error": "user_inactive", "message": str(e), "code": e.error_code},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "authentication_error",
                "message": str(e),
                "code": getattr(e, "error_code", "AUTHENTICATION_ERROR"),
            },
        )


@router.get(
    "/google",
    response_model=GoogleAuthUrlResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Google OAuth2 não configurado"},
    },
    summary="Obter URL de autenticação Google",
    description="Retorna URL para iniciar fluxo de autenticação Google OAuth2",
)
async def get_google_auth_url():
    """Gera URL para autenticação Google OAuth2"""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "oauth2_not_configured",
                "message": "Google OAuth2 não configurado no servidor",
                "code": "OAUTH2_NOT_CONFIGURED",
            },
        )

    # Parâmetros para o Google OAuth2
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
    }

    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    return GoogleAuthUrlResponse(
        auth_url=google_auth_url, redirect_uri=settings.google_redirect_uri
    )


@router.get(
    "/google/callback",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Código de autorização inválido"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Callback do Google OAuth2",
    description="Processa callback do Google OAuth2 e autentica usuário",
)
async def google_oauth2_callback(
    code: str,
    auth_use_case: AuthenticationUseCase = Depends(get_authentication_use_case),
):
    """Processa callback do Google OAuth2"""
    try:
        # Troca o código por um token de acesso
        login_dto = LoginGoogleOAuth2DTO(google_token=code)
        response = await auth_use_case.login_google_oauth2(login_dto)

        return LoginResponse(
            access_token=response.access_token,
            token_type=response.token_type,
            user=UserResponse(**response.user.__dict__),
        )

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_authorization_code",
                "message": str(e),
                "code": e.error_code,
            },
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "user_not_found", "message": str(e), "code": e.error_code},
        )
    except UserInactiveError as e:
        raise HTTPException(
            status_code=403,
            detail={"error": "user_inactive", "message": str(e), "code": e.error_code},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "authentication_error",
                "message": str(e),
                "code": getattr(e, "error_code", "AUTHENTICATION_ERROR"),
            },
        )


@router.post(
    "/google/token",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Token Google inválido"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Login com Google ID Token",
    description="Autentica usuário com ID token do Google OAuth2",
)
async def login_google_oauth2(
    request: LoginGoogleOAuth2Request,
    auth_use_case: AuthenticationUseCase = Depends(get_authentication_use_case),
):
    """Login direto com Google ID Token (para SPAs)"""
    try:
        login_dto = LoginGoogleOAuth2DTO(google_token=request.google_token)

        response = await auth_use_case.login_google_oauth2(login_dto)

        return LoginResponse(
            access_token=response.access_token,
            token_type=response.token_type,
            user=UserResponse(**response.user.__dict__),
        )

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_token", "message": str(e), "code": e.error_code},
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "user_not_found", "message": str(e), "code": e.error_code},
        )
    except UserInactiveError as e:
        raise HTTPException(
            status_code=403,
            detail={"error": "user_inactive", "message": str(e), "code": e.error_code},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "authentication_error",
                "message": str(e),
                "code": getattr(e, "error_code", "AUTHENTICATION_ERROR"),
            },
        )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Token inválido ou expirado"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
    },
    summary="Dados do usuário atual",
    description="Retorna dados do usuário autenticado",
)
async def get_current_user(
    current_user: UserDTO = Depends(get_authenticated_user),
):
    """Retorna dados do usuário autenticado"""
    # Se chegou até aqui, o usuário já foi autenticado pelo middleware
    # current_user nunca será None devido ao middleware

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        primary_municipality_id=current_user.primary_municipality_id,
        municipality_ids=current_user.municipality_ids,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
    )


@router.post(
    "/activate",
    response_model=UserListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Token inválido ou expirado"},
        404: {"model": ErrorResponse, "description": "Token não encontrado"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Ativar conta de usuário",
    description="Ativa conta de usuário via token de convite",
)
async def activate_user_account(
    request: ActivateUserRequest,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    try:
        activate_dto = ActivateUserDTO(
            invitation_token=request.invitation_token, password=request.password
        )

        user_dto = await user_management_use_case.activate_user_account(activate_dto)

        return UserListResponse(**user_dto.__dict__)

    except UserNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "token_not_found",
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
        logger.error(f"Erro na ativação de usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Erro interno na ativação",
                "code": "INTERNAL_ERROR",
            },
        )


@router.post(
    "/users",
    response_model=UserListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Dados inválidos"},
        403: {"model": ErrorResponse, "description": "Permissões insuficientes"},
        409: {"model": ErrorResponse, "description": "Email já existe"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Criar usuário com convite",
    description="Cria novo usuário e envia convite por email",
)
async def create_user_with_invitation(
    request: CreateUserRequest,
    # current_user: AuthenticatedUser,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    # TODO: Implementar middleware de autenticação
    raise HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Endpoint temporariamente desabilitado - middleware em desenvolvimento",
            "code": "NOT_IMPLEMENTED",
        },
    )


@router.get(
    "/users/municipality/{municipality_id}",
    response_model=List[UserListResponse],
    responses={
        403: {"model": ErrorResponse, "description": "Permissões insuficientes"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Listar usuários da prefeitura",
    description="Lista usuários de uma prefeitura específica",
)
async def list_users_by_municipality(
    municipality_id: UUID,
    # current_user: AuthenticatedUser,
    limit: int = 50,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    # TODO: Implementar middleware de autenticação
    raise HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Endpoint temporariamente desabilitado - middleware em desenvolvimento",
            "code": "NOT_IMPLEMENTED",
        },
    )


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=UserListResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Permissões insuficientes"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
        500: {"model": ErrorResponse, "description": "Erro interno"},
    },
    summary="Desativar usuário",
    description="Desativa um usuário específico",
)
async def deactivate_user(
    user_id: UUID,
    # current_user: AuthenticatedUser,
    user_management_use_case: UserManagementUseCase = Depends(
        get_user_management_use_case
    ),
):
    # TODO: Implementar middleware de autenticação
    raise HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Endpoint temporariamente desabilitado - middleware em desenvolvimento",
            "code": "NOT_IMPLEMENTED",
        },
    )
