from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from application.dto.token_dto import (
    AddCreditsRequestDTO,
    UpdateLimitRequestDTO,
)
from application.use_cases.token_management_use_cases import (
    AddExtraCreditsUseCase,
    GetTokenStatusUseCase,
    UpdateMonthlyLimitUseCase,
)
from domain.value_objects.municipality_id import MunicipalityId
from interface.dependencies.container import (
    get_add_credits_use_case,
    get_token_status_use_case,
    get_update_limit_use_case,
)
from interface.schemas.token_schemas import (
    AddCreditsRequest,
    TokenStatusResponse,
    UpdateLimitRequest,
)

router = APIRouter(prefix="/tokens", tags=["Token Management"])


@router.get("/{municipality_id}/status", response_model=TokenStatusResponse)
async def get_token_status(
    municipality_id: UUID,
    get_status_use_case: GetTokenStatusUseCase = Depends(get_token_status_use_case),
):
    """Returns current token status for municipality"""
    try:
        status_dto = await get_status_use_case.execute(MunicipalityId(municipality_id))

        return TokenStatusResponse(
            municipality_id=municipality_id,
            municipality_active=status_dto.municipality_active,
            status=status_dto.status,
            base_limit=status_dto.base_limit,
            extra_credits=status_dto.extra_credits,
            total_limit=status_dto.total_limit,
            consumed=status_dto.consumed,
            remaining=status_dto.remaining,
            usage_percentage=status_dto.usage_percentage,
            period_start=status_dto.period_start,
            period_end=status_dto.period_end,
            days_remaining=status_dto.days_remaining,
            next_due_date=status_dto.next_due_date,
            message=status_dto.message,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/{municipality_id}/credits", response_model=TokenStatusResponse)
async def add_extra_credits(
    municipality_id: UUID,
    request: AddCreditsRequest,
    add_credits_use_case: AddExtraCreditsUseCase = Depends(get_add_credits_use_case),
):
    """Adds extra credits to current period"""
    try:
        request_dto = AddCreditsRequestDTO(
            municipality_id=MunicipalityId(municipality_id),
            tokens=request.tokens,
            reason=request.reason,
        )

        status_dto = await add_credits_use_case.execute(request_dto)

        return TokenStatusResponse(
            municipality_id=municipality_id,
            municipality_active=status_dto.municipality_active,
            status=status_dto.status,
            base_limit=status_dto.base_limit,
            extra_credits=status_dto.extra_credits,
            total_limit=status_dto.total_limit,
            consumed=status_dto.consumed,
            remaining=status_dto.remaining,
            usage_percentage=status_dto.usage_percentage,
            period_start=status_dto.period_start,
            period_end=status_dto.period_end,
            days_remaining=status_dto.days_remaining,
            next_due_date=status_dto.next_due_date,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error adding credits: {str(e)}")


@router.put("/{municipality_id}/limit", response_model=TokenStatusResponse)
async def update_monthly_limit(
    municipality_id: UUID,
    request: UpdateLimitRequest,
    update_limit_use_case: UpdateMonthlyLimitUseCase = Depends(
        get_update_limit_use_case
    ),
):
    """Updates municipality monthly limit (admin only)"""
    try:
        request_dto = UpdateLimitRequestDTO(
            municipality_id=MunicipalityId(municipality_id),
            new_limit=request.new_limit,
            changed_by=request.changed_by or "admin",
        )

        status_dto = await update_limit_use_case.execute(request_dto)

        return TokenStatusResponse(
            municipality_id=municipality_id,
            municipality_active=status_dto.municipality_active,
            status=status_dto.status,
            base_limit=status_dto.base_limit,
            extra_credits=status_dto.extra_credits,
            total_limit=status_dto.total_limit,
            consumed=status_dto.consumed,
            remaining=status_dto.remaining,
            usage_percentage=status_dto.usage_percentage,
            period_start=status_dto.period_start,
            period_end=status_dto.period_end,
            days_remaining=status_dto.days_remaining,
            next_due_date=status_dto.next_due_date,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating limit: {str(e)}")


@router.get("/{municipality_id}/history")
async def get_token_history(
    municipality_id: UUID,
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100, description="Record limit"),
):
    """Returns token period history"""
    # TODO: Implement when needed
    return JSONResponse(
        content={
            "message": "History endpoint will be implemented as needed",
            "municipality_id": str(municipality_id),
        }
    )
