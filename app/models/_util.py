from datetime import datetime, timezone


def utcnow() -> datetime:
    """The single source of 'now' for every model/service in the app.

    Returns a NAIVE datetime whose value is UTC wall-clock time (tzinfo
    stripped after computing it from timezone.utc). This looks backwards,
    but it's required: SQLite has no real timezone-aware column type, so a
    tz-aware datetime written to a column comes back naive on the next
    read (SQLAlchemy's SQLite dialect drops the offset). If utcnow() stays
    aware while values loaded from the DB are naive, any comparison
    between "now" and a stored timestamp (e.g. checking token expiry)
    raises `TypeError: can't compare offset-naive and offset-aware
    datetimes` -- which is exactly what broke the first YouTube sync.

    So the convention project-wide is: every datetime, everywhere
    (columns, this function, anything compared against either) is naive
    and *implicitly* UTC. Local time (e.g. America/Santiago) is only ever
    applied at render time, using Schedule.timezone, never stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
