from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from database.connection import get_db_connection
from database.queries import get_user


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Retrieve current logged in user dict from request session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    try:
        async with get_db_connection() as conn:
            user = await get_user(conn, user_id)
            if user:
                return {
                    "user_id": str(user.id),
                    "email": user.email,
                    "display_name": user.display_name or user.email.split("@")[0],
                }
    except Exception:
        pass

    email = request.session.get("user_email")
    if email:
        return {
            "user_id": str(user_id),
            "email": email,
            "display_name": request.session.get("display_name") or email.split("@")[0],
        }

    return None


async def require_login(request: Request) -> Dict[str, Any]:
    """Dependency / helper to enforce authentication on protected routes."""
    user = await get_current_user(request)
    if not user:
        if request.url.path.startswith("/api"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    request.state.user = user
    return user


require_auth = require_login
