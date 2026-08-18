from __future__ import annotations

from fastapi import APIRouter, Request
from sqlmodel import select

from app.config import get_settings
from app.deps import CurrentUserDep, SessionDep
from app.models import OAuthAccount, OAuthProvider
from app.templating import templates

router = APIRouter()


@router.get("/connections")
def connections(request: Request, user: CurrentUserDep, session: SessionDep):
    settings = get_settings()
    youtube_account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.google, OAuthAccount.is_active == True)  # noqa: E712
    ).first()
    tiktok_account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.tiktok, OAuthAccount.is_active == True)  # noqa: E712
    ).first()

    return templates.TemplateResponse(
        request,
        "connections.html",
        {
            "user": user,
            "google_configured": settings.is_google_configured,
            "tiktok_configured": settings.is_tiktok_configured,
            "youtube_account": youtube_account,
            "tiktok_account": tiktok_account,
        },
    )
