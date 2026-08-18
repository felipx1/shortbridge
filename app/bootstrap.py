"""One-time startup tasks: make sure the admin user row matches whatever
ADMIN_USERNAME / ADMIN_PASSWORD_HASH are currently set in the environment.
This means rotating the admin password is just: regenerate the hash
(scripts/hash_password.py), update the env var, restart the container."""
from __future__ import annotations

from sqlmodel import Session, select

from app.config import get_settings
from app.models import User


def ensure_admin_user(session: Session) -> None:
    settings = get_settings()
    user = session.exec(select(User).where(User.username == settings.admin_username)).first()
    if user is None:
        user = User(username=settings.admin_username, password_hash=settings.admin_password_hash)
        session.add(user)
    elif user.password_hash != settings.admin_password_hash:
        user.password_hash = settings.admin_password_hash
    else:
        return
    session.commit()
