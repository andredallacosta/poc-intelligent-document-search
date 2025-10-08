from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from domain.entities.municipality import Municipality
from domain.entities.user import User
from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.repositories.municipality_repository import MunicipalityRepository
from domain.repositories.user_repository import UserRepository
from domain.value_objects.municipality_id import MunicipalityId
from domain.value_objects.user_id import UserId
from interface.dependencies.container import (
    get_postgres_municipality_repository,
    get_postgres_user_repository,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/municipalities", response_model=dict)
async def create_municipality(
    name: str,
    token_quota: int = 10000,
    municipality_repo: MunicipalityRepository = Depends(
        get_postgres_municipality_repository
    ),
):
    """Creates a new municipality"""
    try:
        municipality = Municipality.create(name=name, token_quota=token_quota)
        await municipality_repo.save(municipality)

        return {
            "id": str(municipality.id),
            "name": municipality.name,
            "token_quota": municipality.token_quota,
            "tokens_consumed": municipality.tokens_consumed,
            "active": municipality.active,
            "created_at": municipality.created_at.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/municipalities", response_model=List[dict])
async def list_municipalities(
    limit: Optional[int] = 50,
    offset: int = 0,
    municipality_repo: MunicipalityRepository = Depends(
        get_postgres_municipality_repository
    ),
):
    """Lists active municipalities"""
    try:
        municipalities = await municipality_repo.find_all_active(
            limit=limit, offset=offset
        )

        return [
            {
                "id": str(m.id),
                "name": m.name,
                "token_quota": m.token_quota,
                "tokens_consumed": m.tokens_consumed,
                "remaining_tokens": m.remaining_tokens,
                "consumption_percentage": m.consumption_percentage,
                "active": m.active,
                "created_at": m.created_at.isoformat(),
            }
            for m in municipalities
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing municipalities: {e}"
        )


@router.get("/municipalities/{municipality_id}", response_model=dict)
async def get_municipality(
    municipality_id: UUID,
    municipality_repo: MunicipalityRepository = Depends(
        get_postgres_municipality_repository
    ),
):
    """Finds municipality by ID"""
    try:
        municipality = await municipality_repo.find_by_id(
            MunicipalityId.from_uuid(municipality_id)
        )

        if not municipality:
            raise HTTPException(status_code=404, detail="Municipality not found")

        return {
            "id": str(municipality.id),
            "name": municipality.name,
            "token_quota": municipality.token_quota,
            "tokens_consumed": municipality.tokens_consumed,
            "remaining_tokens": municipality.remaining_tokens,
            "consumption_percentage": municipality.consumption_percentage,
            "quota_exhausted": municipality.quota_exhausted,
            "quota_critical": municipality.quota_critical,
            "active": municipality.active,
            "created_at": municipality.created_at.isoformat(),
            "updated_at": municipality.updated_at.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users", response_model=dict)
async def create_user(
    name: str,
    email: str,
    municipality_id: Optional[UUID] = None,
    user_repo: UserRepository = Depends(get_postgres_user_repository),
):
    """Creates a new user"""
    try:
        municipality_id_obj = (
            MunicipalityId.from_uuid(municipality_id) if municipality_id else None
        )
        user = User.create(name=name, email=email, municipality_id=municipality_id_obj)
        await user_repo.save(user)

        return {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "municipality_id": (
                str(user.municipality_id) if user.municipality_id else None
            ),
            "is_anonymous": user.is_anonymous,
            "active": user.active,
            "created_at": user.created_at.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users", response_model=List[dict])
async def list_users(
    municipality_id: Optional[UUID] = None,
    limit: Optional[int] = 50,
    offset: int = 0,
    user_repo: UserRepository = Depends(get_postgres_user_repository),
):
    """Lists users"""
    try:
        if municipality_id:
            users = await user_repo.find_by_municipality_id(
                MunicipalityId.from_uuid(municipality_id), limit=limit, offset=offset
            )
        else:
            users = await user_repo.find_all_active(limit=limit, offset=offset)

        return [
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "municipality_id": (
                    str(u.municipality_id) if u.municipality_id else None
                ),
                "is_anonymous": u.is_anonymous,
                "active": u.active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing users: {e}")


@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: UUID,
    user_repo: UserRepository = Depends(get_postgres_user_repository),
):
    """Finds user by ID"""
    try:
        user = await user_repo.find_by_id(UserId.from_uuid(user_id))

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "municipality_id": (
                str(user.municipality_id) if user.municipality_id else None
            ),
            "is_anonymous": user.is_anonymous,
            "has_municipality": user.has_municipality,
            "has_authentication": user.has_authentication,
            "email_domain": user.email_domain,
            "active": user.active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=dict)
async def get_admin_stats(
    municipality_repo: MunicipalityRepository = Depends(
        get_postgres_municipality_repository
    ),
    user_repo: UserRepository = Depends(get_postgres_user_repository),
):
    """Administrative statistics"""
    try:
        total_municipalities = await municipality_repo.count()
        active_municipalities = await municipality_repo.count_active()
        total_users = await user_repo.count()
        active_users = await user_repo.count_active()
        anonymous_users = await user_repo.count_anonymous()

        municipalities_critical_quota = await municipality_repo.find_by_critical_quota()
        municipalities_exhausted_quota = (
            await municipality_repo.find_by_exhausted_quota()
        )

        return {
            "municipalities": {
                "total": total_municipalities,
                "active": active_municipalities,
                "critical_quota": len(municipalities_critical_quota),
                "exhausted_quota": len(municipalities_exhausted_quota),
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "anonymous": anonymous_users,
                "linked": total_users - anonymous_users,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {e}")
