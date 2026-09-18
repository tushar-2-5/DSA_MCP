from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from tools.get_or_create_user import get_or_create_user
from database.connection import get_db_connection
from database.queries import get_user, get_user_by_email

router = APIRouter(tags=["users"])


class UserCreateRequest(BaseModel):
    email: str
    password: Optional[str] = None
    display_name: Optional[str] = None


class UserCreateResponse(BaseModel):
    user_id: str
    email: str
    token: str = ""
    created: bool
    display_name: Optional[str] = None


class UserLookupResponse(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None


@router.post("/api/users", response_model=UserCreateResponse)
@router.post("/api/user", response_model=UserCreateResponse, include_in_schema=False)
async def api_create_or_get_user(payload: UserCreateRequest):
    """Create a new user or fetch existing user by email without authentication."""
    try:
        res = await get_or_create_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
        return UserCreateResponse(
            user_id=res["user_id"],
            email=res["email"],
            token=res.get("token", ""),
            created=res.get("created", res.get("status") == "created"),
            display_name=res.get("display_name"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create or get user: {str(e)}",
        )


@router.get("/api/users/by-email/{email}", response_model=UserLookupResponse)
@router.get("/api/user/{email}/lookup", response_model=UserLookupResponse, include_in_schema=False)
async def api_get_user_by_email(email: str):
    """Fetch user by email address."""
    async with get_db_connection() as conn:
        user = await get_user_by_email(conn, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' not found",
            )
        return UserLookupResponse(
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )


@router.get("/api/users/{user_id}", response_model=UserLookupResponse)
@router.get("/api/user/{user_id}", response_model=UserLookupResponse, include_in_schema=False)
async def api_get_user_by_id(user_id: str):
    """Fetch user by user_id UUID."""
    try:
        UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format. Must be a valid UUID.",
        )

    async with get_db_connection() as conn:
        user = await get_user(conn, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with user_id '{user_id}' not found",
            )
        return UserLookupResponse(
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )
