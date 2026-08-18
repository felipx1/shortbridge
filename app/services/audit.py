from __future__ import annotations

from sqlmodel import Session

from app.models import AuditEvent


def log_event(
    session: Session,
    event_type: str,
    message: str,
    level: str = "info",
    publication_id: int | None = None,
    media_asset_id: int | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        message=message,
        level=level,
        related_publication_id=publication_id,
        related_media_asset_id=media_asset_id,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
