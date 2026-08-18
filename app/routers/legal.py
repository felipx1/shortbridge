"""Public /privacy and /terms pages -- no login required. Exist because
TikTok's app registration form requires both URLs before the app can be
configured at all (not just for review), not because of any tracking or
data-sharing this app actually does -- it doesn't do any. Content here
must stay accurate to what the app really stores/does; see section 41 of
the original spec: no invented claims."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.templating import templates

router = APIRouter()


@router.get("/privacy")
def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {"user": None})


@router.get("/terms")
def terms(request: Request):
    return templates.TemplateResponse(request, "terms.html", {"user": None})
