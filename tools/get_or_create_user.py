from typing import Dict, Any, Optional
from database.connection import get_db_connection
from database.queries import get_user_by_email, create_user


async def get_or_create_user(
    email: str, display_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get an existing user by email or create a new user record if one does not exist.

    Call this tool once at the start of a session or when a user first mentions their email
    to retrieve their stable user_id, then reuse that user_id for all subsequent tool calls
    in the conversation.

    Args:
        email: The email address of the user (required).
        display_name: Optional display name for the user.

    Returns:
        Dict containing user_id and status:
        {"user_id": str, "email": str, "display_name": str or null, "status": "existing" | "created"}
    """
    if not email or not email.strip():
        raise ValueError("email must be a non-empty string.")

    email_clean = email.strip().lower()

    async with get_db_connection() as conn:
        existing_user = await get_user_by_email(conn, email_clean)
        if existing_user:
            return {
                "user_id": str(existing_user.id),
                "email": existing_user.email,
                "display_name": existing_user.display_name,
                "status": "existing",
            }

        new_user = await create_user(conn, email_clean, display_name)
        await conn.commit()

        return {
            "user_id": str(new_user.id),
            "email": new_user.email,
            "display_name": new_user.display_name,
            "status": "created",
        }
