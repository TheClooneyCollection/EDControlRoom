"""System-local timezone adapter, including offsets at past calendar boundaries."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
import time


class SystemLocalTimezone(tzinfo):
    """Delegate calendar conversions to the OS on macOS and Windows.

    datetime.now().astimezone() supplies only today's fixed offset. Keeping
    this adapter as tzinfo lets query windows cross DST changes correctly.
    """

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return dt.replace(tzinfo=None).astimezone().utcoffset() if dt is not None else None

    def tzname(self, dt: datetime | None) -> str | None:
        return dt.replace(tzinfo=None).astimezone().tzname() if dt is not None else None

    def dst(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return None
        naive = dt.replace(tzinfo=None)
        if time.localtime(naive.timestamp()).tm_isdst > 0:
            return naive.astimezone().utcoffset() + timedelta(seconds=time.timezone)
        return timedelta(0)

    def fromutc(self, dt: datetime) -> datetime:
        if dt.tzinfo is not self:
            raise ValueError("fromutc requires this timezone")
        return datetime.fromtimestamp(dt.replace(tzinfo=timezone.utc).timestamp()).replace(tzinfo=self)
