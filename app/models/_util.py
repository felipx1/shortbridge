from datetime import datetime, timezone


def utcnow() -> datetime:
    """Always store timestamps as timezone-aware UTC. Local time (e.g. the
    admin's America/Santiago timezone) is only ever applied at render time."""
    return datetime.now(timezone.utc)
