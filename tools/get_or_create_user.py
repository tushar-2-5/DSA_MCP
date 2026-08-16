import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from database.connection import get_db_connection
from database.queries import get_user_by_email, create_user

SECRET = os.getenv("SECRET_KEY", "recall-mcp-secret-key")


def create_user_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def verify_user_token(token: str, expected_user_id: str) -> bool:
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        if payload["user_id"] != expected_user_id:
            raise ValueError(
                "Access denied: token does not match user_id. "
                "You can only access your own data."
            )
        return True
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired. Call get_or_create_user again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token. Call get_or_create_user first.")


async def get_or_create_user(
    email: str, display_name: Optional[str] = None
) -> Dict[str, Any]:
    """Call this FIRST before any other Recall tool. Pass the email of the person currently using the IDE. Returns user_id and token — store both and pass them to every subsequent tool call.

    Args:
        email: The email address of the user (required).
        display_name: Optional display name for the user.

    Returns:
        Dict containing user_id, token, and status:
        {"user_id": str, "email": str, "display_name": str or null, "token": str, "status": "existing" | "created"}
    """
    if not email or not email.strip():
        raise ValueError("email must be a non-empty string.")

    email_clean = email.strip().lower()

    async with get_db_connection() as conn:
        existing_user = await get_user_by_email(conn, email_clean)
        if existing_user:
            user_id_str = str(existing_user.id)
            return {
                "user_id": user_id_str,
                "email": existing_user.email,
                "display_name": existing_user.display_name,
                "token": create_user_token(user_id_str, existing_user.email),
                "status": "existing",
            }

        new_user = await create_user(conn, email_clean, display_name)
        await conn.commit()
        new_user_id_str = str(new_user.id)

        return {
            "user_id": new_user_id_str,
            "email": new_user.email,
            "display_name": new_user.display_name,
            "token": create_user_token(new_user_id_str, new_user.email),
            "status": "created",
        }

