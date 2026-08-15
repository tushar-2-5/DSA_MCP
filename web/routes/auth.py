from typing import Optional
import bcrypt
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from database.connection import get_db_connection
from database.queries import (
    get_user_with_password_by_email,
    create_user_with_password,
)
from web.auth import get_current_user
from web.rate_limit import limiter

router = APIRouter()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


@router.get("/login", response_class=HTMLResponse)
async def show_login(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None})


@router.get("/signup", response_class=HTMLResponse)
async def show_signup(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="signup.html", context={"user": None})


@router.post("/login")
@limiter.limit("10/minute")
async def handle_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    templates = request.app.state.templates
    email_clean = email.strip().lower()

    async with get_db_connection() as conn:
        user_row = await get_user_with_password_by_email(conn, email_clean)

    if not user_row or not user_row.get("password_hash") or not verify_password(password, user_row["password_hash"]):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid email or password. Please try again."},
            status_code=400,
        )

    user_id = str(user_row["id"])
    request.session["user_id"] = user_id
    request.session["user_email"] = user_row["email"]
    request.session["display_name"] = user_row["display_name"] or user_row["email"].split("@")[0]

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/signup")
@limiter.limit("5/minute")
async def handle_signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: Optional[str] = Form(None),
    display_name: Optional[str] = Form(None),
):
    templates = request.app.state.templates
    email_clean = email.strip().lower()

    if not email_clean or not password:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"error": "Email and password are required."},
            status_code=400,
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"error": "Password must be at least 8 characters."},
            status_code=400,
        )

    if confirm_password is not None and password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"error": "Passwords do not match."},
            status_code=400,
        )

    async with get_db_connection() as conn:
        existing = await get_user_with_password_by_email(conn, email_clean)
        if existing:
            return templates.TemplateResponse(
                request=request,
                name="signup.html",
                context={"error": "An account with this email already exists. Please sign in."},
                status_code=400,
            )

        hashed = hash_password(password)
        new_user = await create_user_with_password(
            conn, email=email_clean, password_hash=hashed, display_name=display_name
        )

    user_id = str(new_user["id"])
    request.session["user_id"] = user_id
    request.session["user_email"] = new_user["email"]
    request.session["display_name"] = new_user["display_name"] or new_user["email"].split("@")[0]

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
