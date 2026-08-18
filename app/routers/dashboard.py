from __future__ import annotations

from fastapi import APIRouter, Request
from sqlmodel import func, select

from app.config import get_settings
from app.deps import CurrentUserDep, SessionDep
from app.models import OAuthAccount, OAuthProvider, Publication, PublicationStatus, YouTubeVideo
from app.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, user: CurrentUserDep, session: SessionDep):
    settings = get_settings()

    youtube_connected = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.google, OAuthAccount.is_active == True)  # noqa: E712
    ).first()
    tiktok_connected = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.tiktok, OAuthAccount.is_active == True)  # noqa: E712
    ).first()

    shorts_count = session.exec(select(func.count()).select_from(YouTubeVideo)).one()

    def count_status(status: PublicationStatus) -> int:
        return session.exec(
            select(func.count()).select_from(Publication).where(Publication.status == status)
        ).one()

    next_publication = session.exec(
        select(Publication)
        .where(Publication.status == PublicationStatus.scheduled)
        .order_by(Publication.scheduled_at)
    ).first()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "dry_run": settings.dry_run,
            "youtube_connected": bool(youtube_connected),
            "youtube_needs_reconnect": bool(youtube_connected and youtube_connected.needs_reconnect),
            "tiktok_connected": bool(tiktok_connected),
            "tiktok_needs_reconnect": bool(tiktok_connected and tiktok_connected.needs_reconnect),
            "shorts_count": shorts_count,
            "published_count": count_status(PublicationStatus.published),
            "draft_count": count_status(PublicationStatus.draft),
            "scheduled_count": count_status(PublicationStatus.scheduled),
            "failed_count": count_status(PublicationStatus.failed),
            "next_publication": next_publication,
        },
    )
