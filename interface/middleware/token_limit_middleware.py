import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from domain.exceptions.token_exceptions import MunicipalityInactiveError
from domain.services.token_limit_service import TokenLimitService
from domain.value_objects.municipality_id import MunicipalityId
from interface.dependencies.container import container

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


class TokenLimitDependency:
    """Dependency for checking token limits following FastAPI patterns"""

    def __init__(self, token_limit_service: TokenLimitService):
        self._token_limit_service = token_limit_service

    async def __call__(self, request: Request) -> Optional[MunicipalityId]:
        """Checks token limit for routes that consume AI"""

        # Only check routes that consume tokens
        if not self._requires_token_check(request.url.path):
            return None

        try:
            # Extract municipality_id from request (implement according to authentication)
            municipality_id = await self._extract_municipality_id(request)

            # Check if has available tokens
            if not await self._token_limit_service.has_available_tokens(
                municipality_id
            ):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "token_limit_exceeded",
                        "message": "Token limit exceeded for this period",
                        "code": "TOKEN_LIMIT_EXCEEDED",
                    },
                )

            return municipality_id

        except MunicipalityInactiveError:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "municipality_inactive",
                    "message": "Municipality with overdue payment. Contact support.",
                    "code": "MUNICIPALITY_INACTIVE",
                },
            )
        except Exception as e:
            logger.error(f"Error in token verification: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_server_error",
                    "message": "Internal error in token control",
                    "code": "INTERNAL_ERROR",
                },
            )

    def _requires_token_check(self, path: str) -> bool:
        """Defines which routes need token verification"""
        ai_routes = [
            "/api/v1/chat/ask",
            # Add other routes that consume AI in the future
        ]
        return any(path.startswith(route) for route in ai_routes)

    async def _extract_municipality_id(self, request: Request) -> MunicipalityId:
        """Extracts municipality_id from request"""
        # TODO: Implement according to authentication system
        # For now, use header or query param for testing

        municipality_header = request.headers.get("X-Municipality-ID")
        if municipality_header:
            return MunicipalityId.from_string(municipality_header)

        # Fallback to query param (development)
        municipality_param = request.query_params.get("municipality_id")
        if municipality_param:
            return MunicipalityId.from_string(municipality_param)

        # Default for development (configure as needed)
        return MunicipalityId.from_string("123e4567-e89b-12d3-a456-426614174000")


# Dependency factory
async def get_token_limit_dependency() -> TokenLimitDependency:
    """Factory to create token control dependency"""
    from interface.dependencies.container import get_token_limit_service
    token_limit_service = await get_token_limit_service()
    return TokenLimitDependency(token_limit_service)


# Type alias for use in endpoints
TokenLimitCheck = Annotated[
    Optional[MunicipalityId], Depends(get_token_limit_dependency)
]
