from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.deps import CurrentUserDep, SessionDep
from app.models import Schedule
from app.models._util import utcnow
from app.security import create_csrf_token, verify_csrf_token
from app.services.audit import log_event
from app.templating import templates

router = APIRouter()


def _get_or_create_schedule(session) -> Schedule:
    schedule = session.exec(select(Schedule).where(Schedule.name == "default")).first()
    if schedule is None:
        schedule = Schedule(name="default")
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
    return schedule


@router.get("/settings")
def settings_form(request: Request, user: CurrentUserDep, session: SessionDep):
    schedule = _get_or_create_schedule(session)
    return templates.TemplateResponse(
        request, "settings.html", {"user": user, "schedule": schedule, "csrf_token": create_csrf_token(), "error": None}
    )


@router.post("/settings")
def settings_submit(
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    csrf_token: str = Form(...),
    daily_times: str = Form(...),
    timezone: str = Form(...),
    monday: bool = Form(False),
    tuesday: bool = Form(False),
    wednesday: bool = Form(False),
    thursday: bool = Form(False),
    friday: bool = Form(False),
    saturday: bool = Form(False),
    sunday: bool = Form(False),
):
    schedule = _get_or_create_schedule(session)

    if not verify_csrf_token(csrf_token):
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"user": user, "schedule": schedule, "csrf_token": create_csrf_token(), "error": "Session expired, please retry."},
            status_code=400,
        )

    # Validate "HH:MM,HH:MM,..." before saving -- a bad value here would
    # silently break the scheduler at run time otherwise.
    try:
        for chunk in daily_times.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            hh, mm = chunk.split(":")
            assert 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
    except Exception:
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"user": user, "schedule": schedule, "csrf_token": create_csrf_token(), "error": "Invalid time format. Use HH:MM,HH:MM,..."},
            status_code=400,
        )

    schedule.daily_times = daily_times
    schedule.timezone = timezone
    schedule.monday = monday
    schedule.tuesday = tuesday
    schedule.wednesday = wednesday
    schedule.thursday = thursday
    schedule.friday = friday
    schedule.saturday = saturday
    schedule.sunday = sunday
    schedule.updated_at = utcnow()
    session.add(schedule)
    session.commit()

    log_event(session, "schedule_updated", f"Schedule updated: {daily_times} ({timezone})")

    return RedirectResponse(url="/settings", status_code=303)
