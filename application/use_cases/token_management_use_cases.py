from application.dto.token_dto import (
    AddCreditsRequestDTO,
    TokenStatusDTO,
    UpdateLimitRequestDTO,
)
from domain.services.token_limit_service import TokenLimitService
from domain.value_objects.municipality_id import MunicipalityId


class GetTokenStatusUseCase:
    """Use case for querying token status"""

    def __init__(self, token_limit_service: TokenLimitService):
        self._token_limit_service = token_limit_service

    async def execute(self, municipality_id: MunicipalityId) -> TokenStatusDTO:
        """Returns complete token status for municipality"""
        status = await self._token_limit_service.get_token_status(municipality_id)

        return TokenStatusDTO(
            municipality_active=status.get("municipality_active", False),
            status=status.get("status", "unknown"),
            base_limit=status.get("base_limit", 0),
            extra_credits=status.get("extra_credits", 0),
            total_limit=status.get("total_limit", 0),
            consumed=status.get("consumed", 0),
            remaining=status.get("remaining", 0),
            usage_percentage=status.get("usage_percentage", 0.0),
            period_start=status.get("period_start"),
            period_end=status.get("period_end"),
            days_remaining=status.get("days_remaining", 0),
            next_due_date=status.get("next_due_date"),
            message=status.get("message"),
        )


class AddExtraCreditsUseCase:
    """Use case for adding extra credits"""

    def __init__(self, token_limit_service: TokenLimitService):
        self._token_limit_service = token_limit_service

    async def execute(self, request: AddCreditsRequestDTO) -> TokenStatusDTO:
        """Adds extra credits to current period"""
        await self._token_limit_service.add_extra_credits(
            municipality_id=request.municipality_id,
            tokens=request.tokens,
            reason=request.reason or "Extra credits purchase",
        )

        # Return updated status
        status = await self._token_limit_service.get_token_status(
            request.municipality_id
        )
        return TokenStatusDTO(**status)


class UpdateMonthlyLimitUseCase:
    """Use case for updating monthly limit"""

    def __init__(self, token_limit_service: TokenLimitService):
        self._token_limit_service = token_limit_service

    async def execute(self, request: UpdateLimitRequestDTO) -> TokenStatusDTO:
        """Updates municipality monthly limit"""
        await self._token_limit_service.update_monthly_limit(
            municipality_id=request.municipality_id,
            new_limit=request.new_limit,
            changed_by=request.changed_by or "system",
        )

        # Return updated status
        status = await self._token_limit_service.get_token_status(
            request.municipality_id
        )
        return TokenStatusDTO(**status)
