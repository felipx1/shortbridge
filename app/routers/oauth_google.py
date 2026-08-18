from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.config import get_settings
from app.deps import CurrentUserDep, SessionDep
from app.models import OAuthAccount, OAuthProvider
from app.models._util import utcnow
from app.providers import youtube
from app.security import create_oauth_state, read_oauth_state, verify_csrf_token
from app.services.audit import log_event
from app.services.crypto import decrypt_token, encrypt_token
from app.services.oauth import ReconnectNeededError
from app.workers.sync import sync_youtube_account

logger = logging.getLogger("shortbridge.oauth.google")

router = APIRouter(prefix="/oauth/google")


@router.get("/start")
def start(user: CurrentUserDep):
    settings = get_settings()
    if not settings.is_google_configured:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured yet")
    state = create_oauth_state("google")
    return RedirectResponse(youtube.build_authorize_url(state))


@router.get("/callback")
def callback(request: Request, user: CurrentUserDep, session: SessionDep):
    settings = get_settings()

    error = request.query_params.get("error")
    if error:
        log_event(session, "oauth_google_denied", f"Google OAuth returned error: {error}", level="warning")
        return RedirectResponse(url="/connections?google_error=1", status_code=303)

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    next_path = read_oauth_state(state, expected_provider="google") if state else None
    if next_path is None or not code:
        log_event(session, "oauth_google_denied", "Google OAuth callback rejected: missing or invalid state", level="warning")
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    tokens = youtube.exchange_code_for_tokens(code)
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    granted_scopes = tokens.get("scope", "")

    channel = youtube.get_own_channel(access_token)
    if channel is None:
        log_event(session, "oauth_google_failed", "Connected to Google but could not read a YouTube channel for this account", level="error")
        return RedirectResponse(url="/connections?google_error=1", status_code=303)

    channel_id = channel["id"]
    channel_title = channel.get("snippet", {}).get("title", channel_id)

    account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.google, OAuthAccount.external_account_id == channel_id)
    ).first()
    if account is None:
        account = OAuthAccount(provider=OAuthProvider.google, external_account_id=channel_id)

    account.display_name = channel_title
    account.encrypted_access_token = encrypt_token(access_token)
    if refresh_token:
        # Google only sends a refresh_token on the first consent (or when
        # prompt=consent forces it, which build_authorize_url always sets)
        # -- but guard anyway rather than overwrite a good one with nothing.
        account.encrypted_refresh_token = encrypt_token(refresh_token)
    account.access_token_expires_at = utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
    account.granted_scopes = granted_scopes
    account.is_active = True
    account.needs_reconnect = False
    account.last_error = None
    account.disconnected_at = None
    account.updated_at = utcnow()
    session.add(account)
    session.commit()

    log_event(session, "oauth_google_connected", f"YouTube channel '{channel_title}' connected")

    return RedirectResponse(url=next_path, status_code=303)


@router.post("/disconnect")
def disconnect(session: SessionDep, user: CurrentUserDep, csrf_token: str = Form(...)):
    if not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid or expired CSRF token")

    account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.google, OAuthAccount.is_active == True)  # noqa: E712
    ).first()
    if account:
        if account.encrypted_refresh_token:
            youtube.revoke_token(decrypt_token(account.encrypted_refresh_token))
        account.is_active = False
        account.encrypted_access_token = None
        account.encrypted_refresh_token = None
        account.disconnected_at = utcnow()
        account.updated_at = utcnow()
        session.add(account)
        session.commit()
        log_event(session, "oauth_google_disconnected", f"YouTube channel '{account.display_name}' disconnected")

    return RedirectResponse(url="/connections", status_code=303)


@router.post("/sync")
def sync_now(session: SessionDep, user: CurrentUserDep, csrf_token: str = Form(...)):
    if not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid or expired CSRF token")

    account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.google, OAuthAccount.is_active == True)  # noqa: E712
    ).first()
    if account is None:
        raise HTTPException(status_code=400, detail="No connected YouTube account")

    try:
        sync_youtube_account(session, account)
    except ReconnectNeededError:
        pass  # already logged + flagged; the Connections page will show it

    return RedirectResponse(url="/library", status_code=303)
