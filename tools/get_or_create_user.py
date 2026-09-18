import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import bcrypt
import jwt
from database.connection import get_db_connection
from database.queries import (
    get_user_with_password_by_email,
    create_user,
    create_user_with_password,
)

logger = logging.getLogger(__name__)

SECRET = os.getenv("SECRET_KEY", "recall-mcp-jwt-secret-key-minimum-32-bytes-long!")


def create_user_token(user_id: str, email: str) -> str:
    try:
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        }
        return jwt.encode(payload, SECRET, algorithm="HS256")
    except Exception as e:
        logger.warning(f"Failed to generate JWT token: {e}")
        return ""


def verify_user_token(token: str, expected_user_id: str) -> bool:
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        if payload.get("user_id") != expected_user_id:
            raise ValueError(
                "Access denied: token does not match user_id. "
                "You can only access your own data."
            )
        return True
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired. Call get_or_create_user again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token. Call get_or_create_user first.")
    except Exception as e:
        raise ValueError(f"Token verification failed: {e}")


async def get_or_create_user(
    email: str,
    password: Optional[str] = None,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Register or fetch a user by email"""
    if not email or not isinstance(email, str) or not email.strip():
        raise ValueError("email must be a non-empty string.")

    email_clean = email.strip().lower()
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
        raise ValueError(f"Invalid email format: '{email_clean}'. Please provide a valid email address.")

    async with get_db_connection() as conn:
        existing_user = await get_user_with_password_by_email(conn, email_clean)
        if existing_user:
            user_id_str = str(existing_user["id"])
            token_str = ""
            try:
                token_str = create_user_token(user_id_str, existing_user["email"])
            except Exception:
                pass
            return {
                "user_id": user_id_str,
                "email": existing_user["email"],
                "display_name": existing_user.get("display_name"),
                "token": token_str,
                "status": "existing",
                "created": False,
            }

        # User does not exist in DB -> Create new user
        if password:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            new_user = await create_user_with_password(conn, email_clean, hashed, display_name)
        else:
            user_obj = await create_user(conn, email_clean, display_name)
            new_user = {"id": user_obj.id, "email": user_obj.email, "display_name": user_obj.display_name}

        await conn.commit()
        new_user_id_str = str(new_user["id"])
        token_str = ""
        try:
            token_str = create_user_token(new_user_id_str, new_user["email"])
        except Exception:
            pass

        return {
            "user_id": new_user_id_str,
            "email": new_user["email"],
            "display_name": new_user.get("display_name"),
            "token": token_str,
            "status": "created",
            "created": True,
        }
