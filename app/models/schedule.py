from datetime import datetime, time
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class Schedule(SQLModel, table=True):
    """Publishing schedule config (section 17). Single active row for the
    MVP (single destination, single cadence) -- modeled as a table instead
    of scattered settings keys so the scheduler and the migration-planning
    calendar (section 36) have one clear source of truth to read/write.
    Times are stored as local wall-clock time in `timezone`; the scheduler
    converts to UTC at run time, correctly across DST."""

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = "default"
    is_active: bool = Field(default=True)

    timezone: str = "America/Santiago"
    # Comma-separated HH:MM in local time, e.g. "10:00,15:00,20:00"
    daily_times: str = "10:00,15:00,20:00"

    monday: bool = Field(default=True)
    tuesday: bool = Field(default=True)
    wednesday: bool = Field(default=True)
    thursday: bool = Field(default=True)
    friday: bool = Field(default=True)
    saturday: bool = Field(default=True)
    sunday: bool = Field(default=True)

    is_paused: bool = Field(default=False)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def time_slots(self) -> list[time]:
        slots = []
        for chunk in self.daily_times.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            hh, mm = chunk.split(":")
            slots.append(time(hour=int(hh), minute=int(mm)))
        return slots

    def active_weekdays(self) -> set[int]:
        """Python weekday(): Monday=0 ... Sunday=6"""
        flags = [self.monday, self.tuesday, self.wednesday, self.thursday,
                 self.friday, self.saturday, self.sunday]
        return {i for i, on in enumerate(flags) if on}
