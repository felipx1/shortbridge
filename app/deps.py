from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Form, HTTPException, Request, status
from sqlmodel import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.models import User
from app.security import read_session_token, verify_csrf_token

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_optional_user(request: Request, session: SessionDep) -> Optional[User]:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        return None
    user_id = read_session_token(token)
    if user_id is None:
        return None
    return session.get(User, user_id)


OptionalUserDep = Annotated[Optional[User], Depends(get_optional_user)]


def require_login(user: OptionalUserDep) -> User:
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


CurrentUserDep = Annotated[User, Depends(require_login)]


def verify_csrf(csrf_token: Annotated[str, Form()]) -> None:
    if not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired CSRF token")
