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
from app.providers import tiktok
from app.security import create_oauth_state, read_oauth_state, verify_csrf_token
from app.services.audit import log_event
from app.services.crypto import decrypt_token, encrypt_token

logger = logging.getLogger("shortbridge.oauth.tiktok")

router = APIRouter(prefix="/oauth/tiktok")


@router.get("/start")
def start(user: CurrentUserDep):
    settings = get_settings()
    if not settings.is_tiktok_configured:
        raise HTTPException(status_code=400, detail="TikTok OAuth is not configured yet")
    state = create_oauth_state("tiktok")
    return RedirectResponse(tiktok.build_authorize_url(state))


@router.get("/callback")
def callback(request: Request, user: CurrentUserDep, session: SessionDep):
    error = request.query_params.get("error")
    if error:
        error_description = request.query_params.get("error_description", error)
        log_event(session, "oauth_tiktok_denied", f"TikTok OAuth returned error: {error_description}", level="warning")
        return RedirectResponse(url="/connections?tiktok_error=1", status_code=303)

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    next_path = read_oauth_state(state, expected_provider="tiktok") if state else None
    if next_path is None or not code:
        log_event(session, "oauth_tiktok_denied", "TikTok OAuth callback rejected: missing or invalid state", level="warning")
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        tokens = tiktok.exchange_code_for_tokens(code)
    except Exception as exc:  # noqa: BLE001
        log_event(session, "oauth_tiktok_failed", f"TikTok token exchange failed: {exc}", level="error")
        return RedirectResponse(url="/connections?tiktok_error=1", status_code=303)

    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    granted_scopes = tokens.get("scope", "")
    open_id = tokens.get("open_id")

    user_info = tiktok.get_user_info(access_token) or {}
    display_name = user_info.get("display_name", open_id)

    account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.tiktok, OAuthAccount.external_account_id == open_id)
    ).first()
    if account is None:
        account = OAuthAccount(provider=OAuthProvider.tiktok, external_account_id=open_id)

    account.display_name = display_name
    account.encrypted_access_token = encrypt_token(access_token)
    if refresh_token:
        account.encrypted_refresh_token = encrypt_token(refresh_token)
    account.access_token_expires_at = utcnow() + timedelta(seconds=tokens.get("expires_in", 86400))
    # granted_scopes is comma-separated from TikTok; has_scope() splits on
    # whitespace (matching Google's space-separated format) -- normalize
    # to space-separated so the same helper works for both providers.
    account.granted_scopes = granted_scopes.replace(",", " ")
    account.is_active = True
    account.needs_reconnect = False
    account.last_error = None
    account.disconnected_at = None
    account.updated_at = utcnow()
    session.add(account)
    session.commit()

    log_event(session, "oauth_tiktok_connected", f"TikTok account '{display_name}' connected (scopes: {account.granted_scopes})")

    return RedirectResponse(url=next_path, status_code=303)


@router.post("/disconnect")
def disconnect(session: SessionDep, user: CurrentUserDep, csrf_token: str = Form(...)):
    if not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid or expired CSRF token")

    account = session.exec(
        select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.tiktok, OAuthAccount.is_active == True)  # noqa: E712
    ).first()
    if account:
        if account.encrypted_access_token:
            tiktok.revoke_token(decrypt_token(account.encrypted_access_token))
        account.is_active = False
        account.encrypted_access_token = None
        account.encrypted_refresh_token = None
        account.disconnected_at = utcnow()
        account.updated_at = utcnow()
        session.add(account)
        session.commit()
        log_event(session, "oauth_tiktok_disconnected", f"TikTok account '{account.display_name}' disconnected")

    return RedirectResponse(url="/connections", status_code=303)
