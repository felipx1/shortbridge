from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.config import get_settings
from app.deps import SessionDep
from app.models import User
from app.security import create_csrf_token, create_session_token, login_rate_limiter, verify_csrf_token, verify_password
from app.services.audit import log_event
from app.templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(
        request, "login.html", {"csrf_token": create_csrf_token(), "error": None}
    )


@router.post("/login")
def login_submit(
    request: Request,
    session: SessionDep,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"

    error = None
    if not verify_csrf_token(csrf_token):
        error = "Your session expired, please try again."
    elif login_rate_limiter.is_blocked(client_ip):
        error = "Too many attempts. Please wait a few minutes and try again."
    else:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            login_rate_limiter.record_attempt(client_ip)
            log_event(session, "login_failed", f"Failed login attempt for username '{username}' from {client_ip}", level="warning")
            error = "Invalid username or password."
        else:
            login_rate_limiter.reset(client_ip)
            from app.models._util import utcnow

            user.last_login_at = utcnow()
            session.add(user)
            session.commit()
            log_event(session, "login_succeeded", f"'{username}' logged in from {client_ip}")

            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(
                key=settings.session_cookie_name,
                value=create_session_token(user.id),
                max_age=settings.session_max_age_seconds,
                httponly=True,
                secure=settings.cookie_secure,
                samesite="lax",
            )
            return response

    return templates.TemplateResponse(
        request, "login.html", {"csrf_token": create_csrf_token(), "error": error}, status_code=400
    )


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(get_settings().session_cookie_name)
    return response
