"""Regression test for the 'can't compare offset-naive and offset-aware
datetimes' bug hit during the first real /oauth/google/sync call: a
datetime written to SQLite and read back is naive, so it must never be
compared against something aware. Reproduces the exact round-trip
(insert -> commit -> fresh read) rather than trusting the fix in theory."""
from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import OAuthAccount, OAuthProvider
from app.models._util import utcnow
from app.services.oauth import _EXPIRY_SAFETY_MARGIN

init_db()

with Session(engine) as session:
    account = OAuthAccount(
        provider=OAuthProvider.google,
        external_account_id="regression-test-channel",
        encrypted_access_token="fake",
        access_token_expires_at=utcnow() + __import__("datetime").timedelta(hours=1),
    )
    session.add(account)
    session.commit()
    account_id = account.id

with Session(engine) as session:
    # Fresh read from a new session -- this is what actually comes back
    # naive from SQLite, unlike the in-memory object right after insert.
    reloaded = session.exec(select(OAuthAccount).where(OAuthAccount.id == account_id)).one()
    assert reloaded.access_token_expires_at.tzinfo is None, "expected a naive datetime back from SQLite"

    # This exact comparison is what raised TypeError before the fix.
    result = reloaded.access_token_expires_at - _EXPIRY_SAFETY_MARGIN > utcnow()
    assert result is True, "a token expiring in 1 hour should look valid"
    print("datetime comparison after SQLite round-trip: OK ->", result)

    session.delete(reloaded)
    session.commit()

print("\nDATETIME FIX REGRESSION TEST PASSED")
