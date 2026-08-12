from fastapi import APIRouter, Request, Form, status
from fastapi.responses import RedirectResponse
from tools.get_or_create_user import get_or_create_user
from web.auth import get_current_user

router = APIRouter()


@router.get("/login")
@router.get("/signup")
async def show_login(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    # Redirect to landing page with signup open or query param
    return RedirectResponse(url="/?action=login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/login")
@router.post("/signup")
async def handle_login(request: Request, email: str = Form(...), display_name: str = Form(None)):
    email_clean = email.strip()
    if not email_clean:
        return RedirectResponse(url="/?error=Invalid+email", status_code=302)

    result = await get_or_create_user(email=email_clean, display_name=display_name)
    user_id = result["user_id"]

    request.session["user_id"] = user_id
    request.session["user_email"] = result["email"]
    request.session["display_name"] = result["display_name"] or result["email"].split("@")[0]

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
