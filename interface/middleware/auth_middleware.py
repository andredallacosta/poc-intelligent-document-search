import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from application.dto.auth_dto import UserDTO
from application.use_cases.authentication_use_case import AuthenticationUseCase
from domain.entities.user import User
from domain.exceptions.auth_exceptions import InvalidTokenError, UserInactiveError
from domain.value_objects.municipality_id import MunicipalityId
from interface.dependencies.container import get_authentication_use_case

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# Classe AuthenticationDependency removida - usando função get_authenticated_user


class MunicipalityExtractor:
    """Extrai prefeitura ativa do usuário autenticado"""

    async def __call__(self, request: Request, current_user: User) -> MunicipalityId:
        """Extrai municipality_id da request ou usuário"""

        # 1. Tenta extrair da request (query param ou header)
        municipality_param = request.query_params.get("municipality_id")
        if municipality_param:
            municipality_id = MunicipalityId.from_string(municipality_param)

            # Verifica se usuário pode acessar esta prefeitura
            if current_user.can_access_municipality(municipality_id):
                return municipality_id
            else:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "municipality_access_denied",
                        "message": "Sem permissão para acessar esta prefeitura",
                        "code": "MUNICIPALITY_ACCESS_DENIED",
                    },
                )

        municipality_header = request.headers.get("X-Municipality-ID")
        if municipality_header:
            municipality_id = MunicipalityId.from_string(municipality_header)

            if current_user.can_access_municipality(municipality_id):
                return municipality_id
            else:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "municipality_access_denied",
                        "message": "Sem permissão para acessar esta prefeitura",
                        "code": "MUNICIPALITY_ACCESS_DENIED",
                    },
                )

        # 2. Fallback para prefeitura principal do usuário
        if current_user.primary_municipality_id:
            return current_user.primary_municipality_id

        # 3. Se não tem prefeitura principal, usar a primeira da lista
        if current_user.municipality_ids:
            return current_user.municipality_ids[0]

        # 4. Fallback final para prefeitura padrão
        return MunicipalityId.from_string("123e4567-e89b-12d3-a456-426614174000")


# Função factory para criar a dependência com injeção correta
async def get_authenticated_user(
    request: Request,
    token: Optional[str] = Depends(security),
    auth_use_case: AuthenticationUseCase = Depends(get_authentication_use_case),
) -> "UserDTO":
    """Dependency function para autenticação JWT - sempre retorna User ou lança exceção"""

    # Para rotas públicas, não aplicar autenticação
    public_routes = [
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/google",
        "/api/v1/auth/activate",
    ]

    # Verifica se é rota pública (comparação exata)
    if request.url.path in public_routes:
        # Para rotas públicas, retornar None seria problemático
        # Melhor não usar este dependency em rotas públicas
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Authentication dependency used on public route",
                "code": "INTERNAL_ERROR",
            },
        )

    # Para rotas protegidas, verificar token
    if not token or not token.credentials:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "Token de acesso obrigatório",
                "code": "AUTHENTICATION_REQUIRED",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        logger.info(f"Auth use case type: {type(auth_use_case)}")
        logger.info("Verifying token...")
        user_dto = await auth_use_case.verify_token(token.credentials)
        logger.info(f"Token verified, user: {user_dto.email}")

        # Para o middleware, vamos usar o DTO diretamente
        # Evita problemas de conversão e campos obrigatórios da entidade
        user = user_dto

        # Adiciona usuário ao contexto da request
        request.state.current_user = user

        return user

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": str(e), "code": e.error_code},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UserInactiveError as e:
        raise HTTPException(
            status_code=403,
            detail={"error": "user_inactive", "message": str(e), "code": e.error_code},
        )
    except Exception as e:
        logger.error(f"Erro na autenticação: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "Erro interno na autenticação",
                "code": "INTERNAL_ERROR",
            },
        )


async def get_current_municipality(
    request: Request, current_user: User = Depends(get_authenticated_user)
) -> MunicipalityId:
    """Dependency function para extração de prefeitura"""
    municipality_extractor = MunicipalityExtractor()
    return await municipality_extractor(request, current_user)


# Type aliases para uso nos endpoints
AuthenticatedUser = Annotated[User, Depends(get_authenticated_user)]
CurrentMunicipality = Annotated[MunicipalityId, Depends(get_current_municipality)]
